# project.json
pbs --server http://220.68.54.36:5000 --api-key API-KEY create-project
# pos_task.csv
#pbs --server http://220.68.54.36:5000 --api-key API-KEY delete-tasks
pbs --server http://220.68.54.36:5000 --api-key API-KEY add-tasks --tasks-file TASKs.csv
# template.html, results.html, long_description.md
pbs --server http://220.68.54.36:5000 --api-key API-KEY update-project
