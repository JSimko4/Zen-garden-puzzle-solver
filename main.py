import math
import random
import time
import xlsxwriter
from typing import Final
from Garden import Garden
from Gardener import Gardener
from Tile import Tile

# Autor: Jakub Šimko
# Dátum vytvorenia: 02.11.2021
# IDE: PyCharm

NOT_RAKED_SAND: Final[int] = 0
ROCK: Final[int] = -1

# nastavenia simulovaného žihania
START_TEMPERATURE: Final[int] = 3600
TEMPERATURE_DECREASE: Final[int] = -3
PHASE_LENGTH: Final[int] = 690

# nastavenia pre vytvorenie suseda
VARIANT2_CHANCE: Final[int] = 2  # 20% sanca vykonania variantu 2
SWAP_POSITIONS_GENES_CHANCE: Final[int] = 5  # 50% šanca na vykonanie variantu 1a) / 1b)

################################################################################
#                                     UTILITY                                  #
################################################################################


# obvod zahrady
def get_perimeter(a, b):
    return 2 * (a + b)


# maximalny pocet genov
def get_max_genome(rows, columns, rocks_count):
    return int(get_perimeter(rows, columns) / 2 + rocks_count)


# nacita mapu zo suboru - velkost a pozicie kamenov
def load_map_from_file(file_name: str):
    rocks_count = 0
    file = open(file_name, "r")

    # zisti rozmery zahrady
    rows, columns = file.readline().split()
    rows, columns = int(rows), int(columns)

    # vytvori mapu zahrady - 2d array
    garden_state = []
    for i in range(rows):
        column = []
        for j in range(columns):
            column.append(0)
        garden_state.append(column)

    # prida kamene na pozicie zadane zo suboru
    for line in file:
        x, y = line.split()
        garden_state[int(x)][int(y)] = ROCK
        rocks_count += 1

    return garden_state, rows, columns, rocks_count


# zapise udaje z priebehu fitness do xls suboru
def write_to_xls(data):
    workbook = xlsxwriter.Workbook('priebeh_fitness.xlsx')
    worksheet = workbook.add_worksheet()

    worksheet.write(0, 0, "Teplota")
    worksheet.write(0, 1, "Najlepšie fitness fázy")
    worksheet.write(0, 2, "Priemerné fitness fázy")

    row = 1
    for arr in data:
        worksheet.write(row, 0, arr[0])
        worksheet.write(row, 1, arr[1])
        worksheet.write(row, 2, arr[2])
        row += 1

    workbook.close()


def get_copy_of_map(garden):
    garden_copy = []

    for i in range(garden.rows):
        column = []
        for j in range(garden.columns):
            column.append(int(garden.state[i][j]))
        garden_copy.append(column)

    return garden_copy


def print_garden(garden):
    for i in range(garden.rows):
        for j in range(garden.columns):
            if len(str(garden.state[i][j])) == 1:
                print(f" {garden.state[i][j]}", end=" ")
            else:
                print(garden.state[i][j], end=" ")
        print(" ")
    print(f"Počet kameňov: {garden.rocks_count}\n")


################################################################################
#                                  ALGORITHM                                   #
################################################################################

def generate_chromosome(rows, columns, rocks_count):
    chromosome = []
    range_numbers = []

    # prida cisla do arrayu od 1 do obvodu
    # vyplyva zo vsetkych zaciatocnych pozicii
    for i in range(1, get_perimeter(rows, columns) + 1):
        range_numbers.append(i)

    random.shuffle(range_numbers)

    # prida prehadzane geny do chromozomu - do určenej max dlzky
    for i in range(0, get_max_genome(rows, columns, rocks_count)):
        gene = range_numbers[i]

        # 50 % sanca na to aby dany gen bol zaporny
        # pri zapornych cislach sa pri narazeni do kamena zahradnik zachova inak - namiesto odbocenia vpravo/
        if random.randint(1, 10) > 5:
            gene = gene * -1

        chromosome.append(gene)

    return chromosome


def get_fitness(garden_state, rows, columns):
    raked_count = 0
    for i in range(rows):
        for j in range(columns):
            if garden_state[i][j] != 0 and garden_state[i][j] != ROCK:
                raked_count += 1

    return raked_count


def get_direction(gene_number, rows, columns):
    if gene_number < 0:
        gene_number = gene_number * -1

    # začiatok v hornej časti zahrady -> pohyb smerom DOLE
    if gene_number <= columns:
        tile = Tile(0, gene_number-1, 1, 0, None)
    # začiatok v pravej časti zahrady -> pohyb smerom DOLAVA
    elif columns < gene_number <= columns + rows:
        tile = Tile(gene_number-columns-1, columns-1, 0, -1, None)
    # začiatok v dolnej časti zahrady -> pohyb smerom HORE
    elif columns + rows < gene_number <= columns*2 + rows:
        tile = Tile(rows-1, columns*2 + rows - gene_number, -1, 0, None)
    # začiatok v lavej časti zahrady -> pohyb smerom DOPRAVA
    else:
        tile = Tile(get_perimeter(rows, columns) - gene_number, 0, 0, 1, None)

    return tile


def in_garden_bounds(row, column, garden_rows, garden_columns):
    if row < 0 or row >= garden_rows or column < 0 or column >= garden_columns:
        return False
    return True


def decide_direction(garden, prev_tile, gene_number):
    # zahradnik sa hybe dole/hore
    if prev_tile.dir_row != 0:
        # policko v pravo aj vlavo je volne -> zahradnik si vyberie na zaklade genu
        in_bounds_right = in_garden_bounds(prev_tile.row, prev_tile.column + 1, garden.rows, garden.columns)
        in_bounds_left = in_garden_bounds(prev_tile.row, prev_tile.column - 1, garden.rows, garden.columns)

        # obidve policka vpravo aj vlavo su volne alebo sa pomocou nich dostaneme von zo zahrady
        if (in_bounds_right and garden.state[prev_tile.row][prev_tile.column + 1] == NOT_RAKED_SAND or not in_bounds_right) and (in_bounds_left and garden.state[prev_tile.row][prev_tile.column - 1] == NOT_RAKED_SAND or not in_bounds_left):
            # ak je cislo/gen zaporny tak si vyberie policko v lavo -> zahradnik zmeni pohyb do lava
            if gene_number < 0:
                # print("VYBERAM SI - MENIM SMER DOLAVA")
                return Tile(prev_tile.row, prev_tile.column - 1, 0, -1, prev_tile)
            # v opačnom pripade si vybera prave poličko -> zahradnik zmeni pohyb doprava
            else:
                # print("VYBERAM SI - MENIM SMER DOPRAVA")
                return Tile(prev_tile.row, prev_tile.column + 1, 0, 1, prev_tile)

        # len prave policko je volne
        elif in_bounds_right and garden.state[prev_tile.row][prev_tile.column + 1] == NOT_RAKED_SAND or not in_bounds_right:
            # print("MENIM SMER DOPRAVA")
            return Tile(prev_tile.row, prev_tile.column + 1, 0, 1, prev_tile)

        # len lave policko je volne
        elif in_bounds_left and garden.state[prev_tile.row][prev_tile.column - 1] == NOT_RAKED_SAND or not in_bounds_left:
            # print("MENIM SMER DOLAVA")
            return Tile(prev_tile.row, prev_tile.column - 1, 0, -1, prev_tile)

        # ani jedno policko neni volne - zahradnik uviazol
        else:
            return None

    # zahradnik sa hybe doprava/dolava
    if prev_tile.dir_col != 0:
        in_bounds_bottom = in_garden_bounds(prev_tile.row + 1, prev_tile.column, garden.rows, garden.columns)
        in_bounds_top = in_garden_bounds(prev_tile.row - 1, prev_tile.column, garden.rows, garden.columns)

        # obidve policka hore aj dole su volne alebo sa pomocou nich dostaneme von zo zahrady
        if (in_bounds_bottom and garden.state[prev_tile.row + 1][prev_tile.column] == NOT_RAKED_SAND or not in_bounds_bottom) and (in_bounds_top and garden.state[prev_tile.row - 1][prev_tile.column] == NOT_RAKED_SAND or not in_bounds_top):
            # ak je cislo/gen zaporny tak si vyberie policko hore -> zahradnik zmeni pohyb smerom HORE
            if gene_number < 0:
                # print("VYBERAM SI - MENIM SMER HORE")
                return Tile(prev_tile.row - 1, prev_tile.column, -1, 0, prev_tile)
            # v opačnom pripade si vyberie policko hore -> zahradnik zmeni pohyb smerom DOLE
            else:
                # print("VYBERAM SI - MENIM SMER DOLE")
                return Tile(prev_tile.row + 1, prev_tile.column, 1, 0, prev_tile)

        # len dolne policko je volne
        elif in_bounds_bottom and garden.state[prev_tile.row + 1][prev_tile.column] == NOT_RAKED_SAND or not in_bounds_bottom:
            # print("MENIM SMER DOLE")
            return Tile(prev_tile.row + 1, prev_tile.column, 1, 0, prev_tile)

        # len horne policko je volne
        elif in_bounds_top and garden.state[prev_tile.row - 1][prev_tile.column] == NOT_RAKED_SAND or not in_bounds_top:
            # print("MENIM SMER HORE")
            return Tile(prev_tile.row - 1, prev_tile.column, -1, 0, prev_tile)

        # ani jedno policko neni volne - zahradnik uviazol
        else:
            return None


def rake_garden(chromosome, garden, get_solution):
    move_flag = 0
    raked_garden = get_copy_of_map(garden)

    for i in range(0, len(chromosome)):
        # print(f"Pokus o hrabanie č. {i+1}")
        curr_tile = get_direction(chromosome[i], garden.rows, garden.columns)

        # test ci moze vstupit do zahrady
        if raked_garden[curr_tile.row][curr_tile.column] == NOT_RAKED_SAND:
            # print(f"Číslo hrabania: {move_flag+1}")

            move_flag += 1
            # pokiaľ zahradnik nevyšiel zo zahrady tak hrabe
            while in_garden_bounds(curr_tile.row, curr_tile.column, garden.rows, garden.columns):
                # kolizia s kamenom - zaahradnik musi vykonat rozhodnutie zmeny smeru
                if raked_garden[curr_tile.row][curr_tile.column] != NOT_RAKED_SAND:
                    # print("NARAZIL SOM")
                    prev_tile = curr_tile.previous
                    curr_tile = decide_direction(Garden(raked_garden, garden.rows, garden.columns, garden.rocks_count), curr_tile.previous, chromosome[i])

                    # zahradnik uviazol / zasekol sa
                    if curr_tile is None:
                        # print("Zasekol som sa, mažem svoje kroky")
                        # vratia sa späť kroky tohto tahu
                        move_flag -= 1
                        while prev_tile is not None:
                            raked_garden[prev_tile.row][prev_tile.column] = 0
                            prev_tile = prev_tile.previous
                        break
                    # po zmene smeru sme vysli von zo zahrady -> konec hrabania v tomto tahu
                    elif not in_garden_bounds(curr_tile.row, curr_tile.column, garden.rows, garden.columns):
                        # print("Zmenou som vyšiel von zo zahrady")
                        break

                raked_garden[curr_tile.row][curr_tile.column] = move_flag
                new_tile = Tile(curr_tile.row + curr_tile.dir_row, curr_tile.column + curr_tile.dir_col,
                                curr_tile.dir_row, curr_tile.dir_col, curr_tile)
                curr_tile = new_tile

    # ak je funkcia zavolaná s umýslom získať pohrabanú záhradu a nie fitness mnícha
    if get_solution:
        return raked_garden

    return get_fitness(raked_garden, garden.rows, garden.columns)


def generate_neighbour(parent_gardener, garden):
    parent_chromosome = parent_gardener.chromosome
    changed_chromosome = parent_chromosome[:]

    # vyberu sa 2 nahodne geny
    rand1 = rand2 = 0
    while rand1 == rand2:
        rand1 = random.randint(0, get_max_genome(garden.rows, garden.columns, garden.rocks_count)-1)
        rand2 = random.randint(0, get_max_genome(garden.rows, garden.columns, garden.rocks_count)-1)

    # 1. variant na najdenie suseda:
    #       a) vymena pozicii genov
    #       b) inverzia v rozhodovani genu
    # 2. variant na najdenie suseda:
    #       a) Vyberie sa 1 nahodny gen ktory bude v chromozone nahradeny inym

    # 90% šanca na vykonanie variantu 1
    variant1_chance = random.randint(1, 10)
    if variant1_chance > VARIANT2_CHANCE:
        # vybere sa nahodne cislo podla ktoreho sa urci ci pri tomto hladani susedov sa bude swapovat start gen
        # alebo  sa obrati/zmeni rozhodovanie pri naraze (+- znak)
        swap_decision_genes_chance = random.randint(1, 10)

        # inverznu sa rozhodovania genov - 50% šanca
        if swap_decision_genes_chance > SWAP_POSITIONS_GENES_CHANCE:
            changed_chromosome[rand1] = changed_chromosome[rand1] * -1
            changed_chromosome[rand2] = changed_chromosome[rand2] * -1
        # prehodia sa pozicie genov
        else:
            tmp = changed_chromosome[rand1]
            changed_chromosome[rand1] = changed_chromosome[rand2]
            changed_chromosome[rand2] = tmp
    else:
        range_numbers = []

        # vsetky mozne geny
        for i in range(1, get_perimeter(garden.rows, garden.columns) + 1):
            range_numbers.append(i)

        existing_gene = True
        while existing_gene:
            existing_gene = False

            # ak nahodne vybrany gen uz je v chromozome tak sa cyklus zopakuje
            # aby sa našiel na vymenu taky gen ktory v chromozome nie je
            rand_gene_num = random.randint(0, get_perimeter(garden.rows, garden.columns)-1)
            for i in range(0, get_max_genome(garden.rows, garden.columns, garden.rocks_count)-1):
                if range_numbers[rand_gene_num] == changed_chromosome[i] \
                        or range_numbers[rand_gene_num] == changed_chromosome[i] * -1:
                    existing_gene = True
                    break

            if existing_gene:
                continue

            # vymeni nahodny gen za novy
            rand3 = random.randint(0, get_max_genome(garden.rows, garden.columns, garden.rocks_count) - 1)
            changed_chromosome[rand3] = range_numbers[rand_gene_num]
            if random.randint(1, 10) > 5:
                changed_chromosome[rand3] = changed_chromosome[rand3] * -1

    return changed_chromosome


def get_neighbour(parent_gardener, garden):
    changed_chromosome = generate_neighbour(parent_gardener, garden)
    changed_fitness = rake_garden(changed_chromosome, garden, False)
    return Gardener(changed_chromosome, changed_fitness)


def simulated_annealing(start_garden, first_gardener):
    results = []     # array na ukladanie priebehu fitness

    counter = 0
    current = best_gardener = first_gardener
    for t in range(START_TEMPERATURE, 0, TEMPERATURE_DECREASE):
        phase_best = phase_average = 0  # premenne na ukladanie priebehu fitness

        counter += 1
        for i in range(0, PHASE_LENGTH):
            new = get_neighbour(current, start_garden)

            # našlo sa riešenie
            if new.fitness == (start_garden.rows * start_garden.columns - start_garden.rocks_count):
                # aktualizovanie hodnot pre vyvoj fitness a nasledny zapis to xls suboru
                phase_best = new.fitness
                phase_average += new.fitness
                phase_average = phase_average / (i+1)
                results.append([t, phase_best, phase_average])
                write_to_xls(results)

                print(f"\nPočet iterácii: {counter * PHASE_LENGTH}")
                return new, counter*PHASE_LENGTH
            # priebezne si uklada najlepsieho zahradnika v pripade ze program nenajde riesenie
            elif new.fitness > best_gardener.fitness:
                best_gardener = new

            # nasiel sa lepsi sused / bol prijaty horsi
            fitness_diff = current.fitness - new.fitness
            if new.fitness > current.fitness or random.uniform(0, 1) < math.exp(-fitness_diff / t):
                current = new

                # zaznamenava priebeh fitness
                phase_average += new.fitness
                if phase_best < new.fitness:
                    phase_best = new.fitness

        # aktualizovanie hodnot pre vyvoj fitness
        phase_average = phase_average/PHASE_LENGTH
        results.append([t, phase_best, phase_average])
        # print(f"TEPLOTA {t}: \t BEST: {phase_best} \t AVERAGE: {phase_average}")

    write_to_xls(results)
    print(f"\nPočet iterácii: {counter*PHASE_LENGTH}")
    return best_gardener, counter*PHASE_LENGTH


def main():
    while True:
        print("Zoznam prikazov:")
        print("help \t\t:\t Vypíše nápovedu ako formatovať súbor z ktorého má program načítať záhradu")
        print("load \t\t:\t Načítanie záhrady zo zadaného súboru")
        print("exit \t\t:\t Ukončí program")
        prikaz = str(input())

        if prikaz == "help":
            print("\nFormát súboru z ktorého sa načíta záhrada vyzerá, že na prvom riadku sa nachádza\n"
                  "počet riadkov a počet stlpcov zahrady a na ďalších riadkoch sa nachádzaju súradnice kameňov.\n")
            print("Formátovanie súboru:")
            print("<počet riadkov> <počet stlpcov>")
            print("<pozicia kamena (riadok)> <pozicia kamena (stlpec)>\n")
            print("Príklad - formát záhrady zo zadania:")
            print("10 12\n1 5\n2 1\n3 4\n4 2\n6 9\n6 10\n")
        elif prikaz == "load":
            print("Zadaj súbor z ktorého má program načítať záhradu:")
            subor = str(input())

            garden_state, rows, columns, rocks_count = load_map_from_file(subor)
            start_garden = Garden(garden_state, rows, columns, rocks_count)

            print("\nNačítaná záhrada:")
            print_garden(start_garden)

            while True:
                print("Zoznam prikazov:")
                print("exec \t:\t Vykonanie zadaného počtu testov na hľadanie riešenia pre zadanú záhradu")
                print("file \t:\t Späť do menu 1 -> možnosť načítať inú záhradu")
                print("exit \t:\t Ukončí program")
                prikaz2 = str(input())

                if prikaz2 == "exec":
                    print("Zadaj počet testov:")
                    tests_num = int(input())
                    print("Začínam...")
                    iterations_total = success = fails = priemer = total_time = 0
                    for i in range(0, tests_num):
                        first_chromosome = generate_chromosome(rows, columns, rocks_count)
                        first_fitness = rake_garden(first_chromosome, start_garden, False)
                        first_gardener = Gardener(first_chromosome, first_fitness)

                        start_time = time.process_time()
                        best_gardener, iterations = simulated_annealing(start_garden, first_gardener)
                        iterations_total += iterations
                        elapsed_time = time.process_time() - start_time

                        solved_garden = rake_garden(best_gardener.chromosome, start_garden, True)
                        print_garden(Garden(solved_garden, rows, columns, rocks_count))

                        print(f"Čas vykonávania prehľadávania: {elapsed_time}s\n")
                        print(f"BEST GARDENER FITNESS: {best_gardener.fitness} CHÝBA {(start_garden.rows * start_garden.columns - start_garden.rocks_count) - best_gardener.fitness}")

                        total_time += elapsed_time
                        if (start_garden.rows * start_garden.columns - start_garden.rocks_count) - best_gardener.fitness == 0:
                            success += 1
                        else:
                            fails += 1
                            priemer += best_gardener.fitness

                    print(f"Počet testov: {tests_num}")
                    print(f"Počet úspešných hľadaní: {success}")
                    print(f"Počet neuspešných hľadaní: {fails}")

                    if fails != 0:
                        print(f"Priemerne ohodnotenie neuspesneho riešenia: {priemer / fails}")
                    else:
                        print(f"Priemerne ohodnotenie neuspesneho riešenia: 0")

                    print(f"Priemerny počet iterácií: {iterations_total / tests_num}")
                    print(f"Priemerna dĺžka prehľadávania: {total_time / tests_num}s")
                elif prikaz2 == "file":
                    break
                elif prikaz2 == "exit":
                    return 0
                else:
                    print("Neznámy príkaz")
        elif prikaz == "exit":
            return 0
        else:
            print("Neznámy príkaz")

#     # chromozom vyuzity pri zobrazeni priebehu fitness
#     # testing_chromosomes_fitness = [10, 42, -7, -14, -39, 11, -31, -26, 44, 18, -35, -16, 43, -1, -36, -29, 9, 32, 5, -28, -2, 22, -24, -40, 27, -17, -19, -38]
#
# Chromozomy vyuzite v dokumentacii na testovanie s rovnakym zač. chromozomom
#     testing_chromosomes = [
#         [-34, 2, -14, -29, 37, 20, -8, -40, 38, -42, 24, -31, 33, 22, -21, -41, -17, 18, -9, 15, -23, 4,43, 13, 30, -10, -32, -35],
#         [-42, -36, 11, 35, 38, 28, 12, 24, -33, 25, 8, 6, 29, 14, -34, 40, -15, -23, 16, 4, -26, 17,-30, 32, -39, -10, -27, 31],
#         [44, 38, -14, -40, 43, -29, 9, 4, 6, -7, -21, -25, 2, 18, 41, 15, -35, -30, -22, -1, 19, -39,13, 27, 28, -3, -17, 37],
#         [-15, 37, -14, -30, -1, -40, -9, -38, 17, 16, -23, -2, -7, 31, 35, 34, 39, -19, -3, 36, -32, 26,28, -43, 8, 21, -24, -4],
#         [-28, 37, -3, -7, -16, -12, -14, -19, -38, -25, -43, 30, 40, 39, 27, 34, 13, -41, -35, -17, -15,11, 10, -1, 20, -21, -31, 23],
#         [-1, 31, -18, -35, 16, 41, 3, -6, -23, -28, 24, 34, 42, -17, -2, -32, -19, -26, 11, -14, -21,-12, -40, -36, 13, 9, -25, -44],
#         [-4, -13, -2, -32, -15, 35, -22, 21, 10, 39, -3, 18, 23, 20, -8, -17, 25, 7, 36, -14, 12, -42,34, 26, 9, -6, 11, -37],
#         [-31, -42, -44, 21, -27, 37, 32, 3, 15, 22, 14, -17, -24, 30, -5, -16, -19, 26, -38, 13, -18,-1, -34, 28, 12, 9, -43, 29],
#         [-23, 40, -10, 26, -25, 41, -15, 44, 9, 42, -17, -3, 14, 43, 2, 38, 12, 39, -19, 34, 5, 4, -13, 11, -30, 37, 32, 18],
#         [10, 42, -7, -14, -39, 11, -31, -26, 44, 18, -35, -16, 43, -1, -36, -29, 9, 32, 5, -28, -2, 22,-24, -40, 27, -17, -19, -38]
#     ]


if __name__ == "__main__":
    main()
