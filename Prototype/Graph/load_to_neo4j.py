"""
load_to_neo4j.py

Reads the synthetic investigation CSVs from data/ and loads them into a
Neo4j graph database as nodes and relationships, ready for link analysis.

Connection: bolt://localhost:7687 (user: neo4j / password: password123)

Run:
    python load_to_neo4j.py
"""

import csv
import os
from neo4j import GraphDatabase

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

DATA_DIR = "."
BATCH_SIZE = 500  # rows per UNWIND batch


def data_path(filename):
    return os.path.join(DATA_DIR, filename)


def read_csv(filename):
    """Read a CSV file from the data/ folder into a list of dicts."""
    with open(data_path(filename), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def chunked(rows, size):
    """Yield successive `size`-sized chunks from a list."""
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Running counters for the final summary
        self.counts = {
            "Person": 0, "Phone": 0, "Account": 0, "Vehicle": 0, "Case": 0,
            "OWNS_PHONE": 0, "OWNS_ACCOUNT": 0, "OWNS_VEHICLE": 0,
            "CALLED": 0, "TRANSACTED_WITH": 0, "INVOLVED_IN": 0,
        }

    def close(self):
        self.driver.close()

    def run_batched(self, query, rows, label):
        """Run a parameterised Cypher query in UNWIND batches, and report progress."""
        total = len(rows)
        if total == 0:
            print(f"  (no rows for {label}, skipping)")
            return
        done = 0
        for batch in chunked(rows, BATCH_SIZE):
            with self.driver.session() as session:
                session.run(query, rows=batch)
            done += len(batch)
            print(f"  {label}: {done}/{total} rows processed")

    # -----------------------------------------------------------------
    # Wipe the database clean before loading
    # -----------------------------------------------------------------
    def clear_database(self):
        print("Clearing existing database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared.\n")

    # -----------------------------------------------------------------
    # Node loaders
    # -----------------------------------------------------------------
    def load_persons(self, rows):
        query = """
        UNWIND $rows AS row
        MERGE (p:Person {person_id: row.person_id})
        SET p.name = row.name,
            p.age = toInteger(row.age),
            p.gender = row.gender,
            p.address = row.address,
            p.city = row.city
        """
        print("Loading Person nodes...")
        self.run_batched(query, rows, "Person")
        self.counts["Person"] = len(rows)

    def load_phones(self, rows):
        # phones.csv gives us both the Phone nodes and the Person-OWNS-Phone edges
        query = """
        UNWIND $rows AS row
        MERGE (ph:Phone {phone_number: row.phone_number})
        """
        print("Loading Phone nodes...")
        self.run_batched(query, rows, "Phone")
        self.counts["Phone"] = len({r["phone_number"] for r in rows})

    def load_accounts(self, rows):
        query = """
        UNWIND $rows AS row
        MERGE (a:Account {account_id: row.account_id})
        SET a.bank_name = row.bank_name
        """
        print("Loading Account nodes...")
        self.run_batched(query, rows, "Account")
        self.counts["Account"] = len(rows)

    def load_vehicles(self, rows):
        query = """
        UNWIND $rows AS row
        MERGE (v:Vehicle {plate_number: row.plate_number})
        SET v.vehicle_type = row.vehicle_type
        """
        print("Loading Vehicle nodes...")
        self.run_batched(query, rows, "Vehicle")
        self.counts["Vehicle"] = len(rows)

    def load_cases(self, rows):
        query = """
        UNWIND $rows AS row
        MERGE (c:Case {case_id: row.case_id})
        SET c.description = row.description,
            c.location = row.location
        """
        print("Loading Case nodes...")
        self.run_batched(query, rows, "Case")
        self.counts["Case"] = len(rows)

    # -----------------------------------------------------------------
    # Relationship loaders
    # -----------------------------------------------------------------
    def load_owns_phone(self, rows):
        query = """
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row.owner_id})
        MATCH (ph:Phone {phone_number: row.phone_number})
        MERGE (p)-[:OWNS]->(ph)
        """
        print("Linking Person-OWNS->Phone...")
        self.run_batched(query, rows, "OWNS (Phone)")
        self.counts["OWNS_PHONE"] = len(rows)

    def load_owns_account(self, rows):
        query = """
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row.owner_id})
        MATCH (a:Account {account_id: row.account_id})
        MERGE (p)-[:OWNS]->(a)
        """
        print("Linking Person-OWNS->Account...")
        self.run_batched(query, rows, "OWNS (Account)")
        self.counts["OWNS_ACCOUNT"] = len(rows)

    def load_owns_vehicle(self, rows):
        query = """
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row.owner_id})
        MATCH (v:Vehicle {plate_number: row.plate_number})
        MERGE (p)-[:OWNS]->(v)
        """
        print("Linking Person-OWNS->Vehicle...")
        self.run_batched(query, rows, "OWNS (Vehicle)")
        self.counts["OWNS_VEHICLE"] = len(rows)

    def load_calls(self, rows):
        query = """
        UNWIND $rows AS row
        MATCH (c1:Phone {phone_number: row.caller_number})
        MATCH (c2:Phone {phone_number: row.receiver_number})
        MERGE (c1)-[r:CALLED {timestamp: row.timestamp}]->(c2)
        SET r.duration_seconds = toInteger(row.duration_seconds)
        """
        print("Linking Phone-CALLED->Phone...")
        self.run_batched(query, rows, "CALLED")
        self.counts["CALLED"] = len(rows)

    def load_transactions(self, rows):
        query = """
        UNWIND $rows AS row
        MATCH (a1:Account {account_id: row.from_account})
        MATCH (a2:Account {account_id: row.to_account})
        MERGE (a1)-[r:TRANSACTED_WITH {timestamp: row.timestamp}]->(a2)
        SET r.amount = toFloat(row.amount)
        """
        print("Linking Account-TRANSACTED_WITH->Account...")
        self.run_batched(query, rows, "TRANSACTED_WITH")
        self.counts["TRANSACTED_WITH"] = len(rows)

    def load_case_links(self, case_rows):
        # linked_person_ids is a comma-separated string in cases.csv;
        # flatten it into one (person_id, case_id) row per link first.
        link_rows = []
        for row in case_rows:
            person_ids = [pid.strip() for pid in row["linked_person_ids"].split(",") if pid.strip()]
            for pid in person_ids:
                link_rows.append({"person_id": pid, "case_id": row["case_id"]})

        query = """
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row.person_id})
        MATCH (c:Case {case_id: row.case_id})
        MERGE (p)-[:INVOLVED_IN]->(c)
        """
        print("Linking Person-INVOLVED_IN->Case...")
        self.run_batched(query, link_rows, "INVOLVED_IN")
        self.counts["INVOLVED_IN"] = len(link_rows)

    # -----------------------------------------------------------------
    # Verification summary (actual counts pulled from the database)
    # -----------------------------------------------------------------
    def fetch_actual_counts(self):
        queries = {
            "Person": "MATCH (n:Person) RETURN count(n) AS c",
            "Phone": "MATCH (n:Phone) RETURN count(n) AS c",
            "Account": "MATCH (n:Account) RETURN count(n) AS c",
            "Vehicle": "MATCH (n:Vehicle) RETURN count(n) AS c",
            "Case": "MATCH (n:Case) RETURN count(n) AS c",
            "OWNS": "MATCH ()-[r:OWNS]->() RETURN count(r) AS c",
            "CALLED": "MATCH ()-[r:CALLED]->() RETURN count(r) AS c",
            "TRANSACTED_WITH": "MATCH ()-[r:TRANSACTED_WITH]->() RETURN count(r) AS c",
            "INVOLVED_IN": "MATCH ()-[r:INVOLVED_IN]->() RETURN count(r) AS c",
        }
        results = {}
        with self.driver.session() as session:
            for label, query in queries.items():
                results[label] = session.run(query).single()["c"]
        return results


def main():
    # -----------------------------------------------------------------
    # Read all CSVs up front
    # -----------------------------------------------------------------
    print("Reading CSV files from data/ ...")
    persons = read_csv("persons.csv")
    phones = read_csv("phones.csv")
    accounts = read_csv("bank_accounts.csv")
    vehicles = read_csv("vehicles.csv")
    calls = read_csv("call_records.csv")
    transactions = read_csv("transactions.csv")
    cases = read_csv("cases.csv")
    print(
        f"Loaded from disk: {len(persons)} persons, {len(phones)} phones, "
        f"{len(accounts)} accounts, {len(vehicles)} vehicles, {len(calls)} calls, "
        f"{len(transactions)} transactions, {len(cases)} cases.\n"
    )

    loader = Neo4jLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        # Start from a clean database
        loader.clear_database()

        # Nodes first
        loader.load_persons(persons)
        loader.load_phones(phones)
        loader.load_accounts(accounts)
        loader.load_vehicles(vehicles)
        loader.load_cases(cases)
        print()

        # Then relationships (both endpoints now exist)
        loader.load_owns_phone(phones)
        loader.load_owns_account(accounts)
        loader.load_owns_vehicle(vehicles)
        loader.load_calls(calls)
        loader.load_transactions(transactions)
        loader.load_case_links(cases)
        print()

        # -----------------------------------------------------------------
        # Final summary, verified against the database itself
        # -----------------------------------------------------------------
        actual = loader.fetch_actual_counts()
        print("=" * 50)
        print("LOAD COMPLETE - Summary (verified from database)")
        print("=" * 50)
        print("Nodes:")
        print(f"  Person   : {actual['Person']}")
        print(f"  Phone    : {actual['Phone']}")
        print(f"  Account  : {actual['Account']}")
        print(f"  Vehicle  : {actual['Vehicle']}")
        print(f"  Case     : {actual['Case']}")
        print("Relationships:")
        print(f"  OWNS             : {actual['OWNS']}")
        print(f"  CALLED           : {actual['CALLED']}")
        print(f"  TRANSACTED_WITH  : {actual['TRANSACTED_WITH']}")
        print(f"  INVOLVED_IN      : {actual['INVOLVED_IN']}")
        print("=" * 50)

    finally:
        loader.close()


if __name__ == "__main__":
    main()
