import csv
import random
import sys
from pathlib import Path

input_files = []

input_files_00 = ["includes/scenarios/generated/workload_00/workload00.txt"]

blocks_directory_30 = "includes/scenarios/generated/workload_30"
blocks_directory_path = Path(blocks_directory_30)
input_files_30 = [str(blocks_directory_path.joinpath("workload30_{}.txt".format(i))) for i in range(1, 13)]

blocks_directory_70 = "includes/scenarios/generated/workload_70"
blocks_directory_path = Path(blocks_directory_70)
input_files_70 = [str(blocks_directory_path.joinpath("workload70_{}.txt".format(i))) for i in range(1, 13)]

input_csv_tri = 'includes/experimental_design/wrist_only_29062023_P19_20.csv'
csv_data_tri = []
with open(input_csv_tri, 'r') as file:
    reader = csv.reader(file, delimiter=';')
    csv_data_tri = list(reader)

series_order = {}
for row in csv_data_tri[1:]:
    series = int(row[0])
    order = row[1:]
    series_order[series] = order

if len(sys.argv) > 1:
    input_argument = int(sys.argv[1])
else:
    print("Veuillez spécifier un argument.")
    sys.exit(1)

if input_argument not in series_order:
    print(f"Aucun ordre trouvé pour l'argument {input_argument}.")
    sys.exit(1)

order_list = series_order[input_argument]

for letter in order_list:
    match letter:
        case 'A' | 'D':
            input_files.append(input_files_00)
        case 'B' | 'E':
            input_files.append(random.sample(input_files_30, 1))
        case 'C' | 'F':
            input_files.append(random.sample(input_files_70, 1))

print(order_list)

current_hour = 0
current_minute = 0
current_second = 0
time_increment = 12
block_count = 0
block_0_start = False

output_file = F"includes/scenarios/generated/participants/participant-{input_argument}.txt"
with open(output_file, "w") as output:
    for file_list in input_files:
        for file in file_list:
            with open(file, "r") as input:
                lines = input.readlines()
                #output.writelines(lines)
                for line in lines:
                    if block_count == 0:
                        if line.startswith("# Name"):
                            if line.startswith("# Name:workload00"):
                                block_0_start = True
                        parts = line.split(";")
                        if not parts[-1].strip().endswith('stop') and not parts[-1].strip().endswith('hide') and not parts[-1].strip().endswith('pause') and not parts[-1].strip().endswith('show') and not parts[-1].strip().endswith('resume'):
                            new_line = ";".join(parts)
                            output.write(new_line)
                    elif 0 < block_count < 5:
                        if line.startswith("# Name:"):
                            current_minute += time_increment
                            current_hour += current_minute // 60
                            current_minute = current_minute % 60
                            output.write(line)
                        if line.startswith("# Technical"):
                            output.write(line)
                        if line.strip() and not line.startswith("#"):
                            parts = line.split(";")
                            time_parts = parts[0].split(":")
                            hour = int(time_parts[0])
                            minute = int(time_parts[1])
                            second = int(time_parts[2])
                            new_hour = current_hour + hour
                            new_minute = current_minute + minute
                            new_second = current_second + second
                            if new_second >= 60:
                                new_second -= 60
                                new_minute += 1
                            if new_minute >= 60:
                                new_minute -= 60
                                new_hour += 1
                            parts[0] = f"{new_hour:02d}:{new_minute:02d}:{new_second:02d}"
                            if not parts[-2].strip().endswith('genericscales'):
                                if block_0_start == 1:
                                    if not parts[-1].strip().endswith('stop') and not parts[-2].strip().endswith('tactonsinfo'):
                                        new_line = ";".join(parts)
                                        output.write(new_line)
                                else:
                                    if not parts[-1].strip().endswith('start') and not parts[-1].strip().endswith('stop'):
                                        new_line = ";".join(parts)
                                        output.write(new_line)
                            else:
                                new_line = ";".join(parts)
                                output.write(new_line)
                    else:
                        if line.startswith("# Name:"):
                            current_minute += time_increment
                            current_hour += current_minute // 60
                            current_minute = current_minute % 60
                            output.write(line)
                        if line.startswith("# Technical"):
                            output.write(line)
                        if line.strip() and not line.startswith("#"):
                            parts = line.split(";")
                            time_parts = parts[0].split(":")
                            hour = int(time_parts[0])
                            minute = int(time_parts[1])
                            second = int(time_parts[2])
                            new_hour = current_hour + hour
                            new_minute = current_minute + minute
                            new_second = current_second + second
                            if new_second >= 60:
                                new_second -= 60
                                new_minute += 1
                            if new_minute >= 60:
                                new_minute -= 60
                                new_hour += 1
                            parts[0] = f"{new_hour:02d}:{new_minute:02d}:{new_second:02d}"
                            if not parts[-2].strip().endswith('genericscales'):
                                if not parts[-1].strip().endswith('start'):
                                    new_line = ";".join(parts)
                                    output.write(new_line)
                            else:
                                new_line = ";".join(parts)
                                output.write(new_line)
                if block_count != 0:
                    block_0_start = False
            block_count += 1
