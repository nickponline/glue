from dataclasses import dataclass

@dataclass
class Config:
    PREFIX = 'www'
    GQL_PREFIX = 'api'
    ISSUE_TYPE = 'IssueType:624'

config = Config()