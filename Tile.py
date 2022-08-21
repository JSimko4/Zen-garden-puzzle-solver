class Tile:
    def __init__(self, row, column, dir_row, dir_col, previous):
        self.row = row
        self.column = column

        #  1 -> pohyb/hrabanie smerom DOLE
        # -1 -> pohyb/hrabanie smerom HORE
        #  0 -> nehybe sa v tomto smere
        self.dir_row = dir_row

        #  1 -> pohyb/hrabanie smerom DOPRAVA
        # -1 -> pohyb/hrabanie smerom DOLAVA
        #  0 -> nehybe sa v tomto smere
        self.dir_col = dir_col

        # prechadzajuce policko
        self.previous = previous

    def print_info(self):
        print(f"X: {self.row} Y: {self.column}")
        if self.dir_row == 1:
            print("HYBEM SA DOLE")
        elif self.dir_row == -1:
            print("HYBEM SA HORE")

        if self.dir_col == 1:
            print("HYBEM SA DOPRAVA")
        elif self.dir_col == -1:
            print("HYBEM SA DOLAVA")
