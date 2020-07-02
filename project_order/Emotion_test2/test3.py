import json

data = []
with open('/home/gocks456/project_order/Emotion_test/sentence_temp.json', encoding='utf-8') as f, \
		open('/home/gocks456/project_order/Emotion_test/sentence_list_1.json', "w", encoding='utf-8') as ff:
	for line in f:
		data.append(json.loads(line))

	ff.write(json.dumps(data, ensure_ascii=False))
