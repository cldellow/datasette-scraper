current_schema_version = 1000000;

schema = """
PRAGMA user_version = {};
""".format(current_schema_version) + """
"""
