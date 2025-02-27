import sys

from crossword import *

import queue


class CrosswordCreator():

    def __init__(self, crossword: Crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment: dict):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        Remove words that do not match the variable's length.
        """
        for var in self.domains:
            self.domains[var] = {word for word in self.domains[var] if len(word) == var.length}
            
            # If no valid words remain, raise an error
            if not self.domains[var]:
                raise ValueError(f"No values left for variable {var}")


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        Remove values from `self.domains[x]` that do not have a possible 
        corresponding value in `self.domains[y]`.
        
        Return True if a revision was made, otherwise False.
        """
        revised = False

        # Get the overlap position (if exists)
        if (x, y) not in self.crossword.overlaps or self.crossword.overlaps[(x, y)] is None:
            return False  # No constraint between x and y

        i, j = self.crossword.overlaps[(x, y)]  # Overlapping index

        # Keep only values that have at least one valid pair in `y`
        values_to_remove = set()

        for vx in self.domains[x]:
            # Check if there is any vy in y's domain that satisfies the constraint
            if not any(vx[i] == vy[j] for vy in self.domains[y]):
                values_to_remove.add(vx)

        # Remove invalid values
        if values_to_remove:
            self.domains[x] -= values_to_remove
            revised = True

        return revised
    
    def get_arcs(self):
        """
        Generate all arcs (X, Y) where X and Y are neighbors in the CSP.

        Returns:
            A list of tuples (X, Y), where X and Y are connected variables.
        """
        arcs = []
        for X in self.crossword.variables:  # Iterate through all variables
            for Y in self.crossword.neighbors(X):  # Get X's neighbors
                arcs.append((X, Y))  # Add (X, Y) to the list
        return arcs

    def ac3(self, arcs=None):
        """
        Enforce arc consistency for all variables in the CSP.

        If `arcs` is None, initialize the queue with all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domain is empty.
        Return False if any domain becomes empty (i.e., the problem is unsolvable).
        """
        if arcs is None:
            queue = self.get_arcs()  # Get all arcs in the problem
        else:
            queue = arcs[:]  # Copy the given arcs to process

        while queue:
            X, Y = queue.pop(0)  # Get an arc (X, Y)

            if self.revise(X, Y):  # If we revise X's domain
                if not self.domains[X]:  # If X's domain is empty, no solution
                    return False
                
                # Add all neighbors of X (except Y) back to the queue
                for Z in self.crossword.neighbors(X):
                    if Z != Y:
                        queue.append((Z, X))

        return True  # If no domains are empty, return True


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return all(var in assignment and assignment[var] is not None for var in self.crossword.variables)

    def consistent(self, assignment: dict):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check uniqueness of words
        values = list(assignment.values())
        if len(values) != len(set(values)):
            return False  # Duplicate words found

        for var, val in assignment.items():
            if val is None:
                continue

            # Check length constraint (word must fit in the variable's length)
            if len(val) != var.length:
                return False

            # Check conflicts with neighbors based on overlaps
            for other_var in self.crossword.neighbors(var):
                if other_var not in assignment:
                    continue  # Skip unassigned neighbors
                
                other_val = assignment[other_var]
                if other_val is None:
                    continue
                
                # Ensure overlap exists
                if (var, other_var) in self.crossword.overlaps:
                    var_pos, other_var_pos = self.crossword.overlaps[(var, other_var)]
                    
                    # Ensure the words match at their overlap position
                    if val[var_pos] != other_val[other_var_pos]:
                        return False

        return True  # Assignment is consistent

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, sorted by 
        the number of values they rule out for neighboring variables.
        The first value in the list should be the one that rules out 
        the fewest values for neighbors.
        """
        def count_conflicts(value):
            """Count how many values this choice would rule out for neighbors."""
            return sum(
                len(self.domains[neighbor]) - 
                len([val for val in self.domains[neighbor] if val != value])
                for neighbor in self.crossword.neighbors(var) 
                if neighbor not in assignment
            )

        # Sort domain values by the least number of conflicts
        return sorted(self.domains[var], key=count_conflicts)


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree (most connected variable). If there is a tie, return any of them.
        """
        unassigned = [var for var in self.domains if var not in assignment]

        # Compute degree based on how many other variables share values with this variable
        def degree(var):
            return sum(1 for other in self.domains if other != var and set(self.domains[var]) & set(self.domains[other]))

        # Sort first by MRV, then by highest degree
        return min(unassigned, key=lambda var: (len(self.domains[var]), -degree(var)))


        
    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for word in self.order_domain_values(var, assignment):
            assignment[var] = word
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result is not None:
                    return result
            assignment[var] = None
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
