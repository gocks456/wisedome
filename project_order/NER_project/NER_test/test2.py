import csv
import json

date = []

with open('/home/gocks456/project_order/NER_test/200408.csv', "r", encoding="utf-8", newline="") as input_file, \
		open('/home/gocks456/project_order/NER_test/test1.json', "w", encoding="utf-8", newline="") as output_file:

	reader = csv.reader(input_file)
	# 첫 줄은 col_names 리스트로 읽어 놓고
	col_names = next(reader)
	# 그 다음 줄부터 zip으로 묶어서 json으로 dumps
	for cols in reader:
		while(True):
			if(len(cols) == 5):
				break
			cols[0] = cols[0] + cols[1]
			del cols[1]

		doc = {col_name: col for col_name, col in zip(col_names, cols)}
		print(json.dumps(doc, ensure_ascii=False), file=output_file)
