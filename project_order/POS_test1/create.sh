# project.json
pbs --server http://220.68.54.36:5000 --api-key 3e9168a4-4879-46be-ac9c-65e022af2df0 create-project
# pos_task.csv
pbs --server http://220.68.54.36:5000 --api-key 3e9168a4-4879-46be-ac9c-65e022af2df0 add-tasks --tasks-file TASKs.csv
# template.html, results.html, long_description.md
pbs --server http://220.68.54.36:5000 --api-key 3e9168a4-4879-46be-ac9c-65e022af2df0 update-project
