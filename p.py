from crossword import *

# crossword = Crossword()

def enforce_node_consistency(domains: dict):
    for var in domains:
        domains[var] = {word for word in domains[var] if len(word) == var.length}

        if not domains[var]:
            raise ValueError(f"No Value found for {var}")