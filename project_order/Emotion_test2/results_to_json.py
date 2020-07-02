import json
import re

data = []

with open('/home/gocks456/emotion_test1_task_run.json', "r", encoding="utf-8") as input_file1, \
		open('/home/gocks456/emotion_test2_task_run.json', "r", encoding="utf-8") as input_file2, \
		open('/home/gocks456/emotion_results.json', "w", encoding="utf-8") as output_file:


	json_data1 = json.load(input_file1)
	json_data2 = json.load(input_file2)

	for row in json_data2:
		temp = dict()
		s_row = row["info"].split('+')
		temp["sentence"] = s_row[0]
		temp["obj"] = s_row[1]
		data.append(temp)
	for row in json_data1:
		s_row = row["info"].split('+')
		for temp in data:
			if temp["sentence"] == s_row[0]:
				temp["pos"] = s_row[1]

	print(json.dump(data, output_file, indent="\t", ensure_ascii=False))
