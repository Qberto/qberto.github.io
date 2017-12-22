import glob, os

desc_dir = ""

os.chdir(desc_dir)

for file in glob.glob("*.txt"):
	print(file)
	file_num = file.split(".")[0]
	print(file_num)
	with open(file, 'w') as text_file:
		text_file.write("{0}. Placeholder description text").format(str(file_num))
		