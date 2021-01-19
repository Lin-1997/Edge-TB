## dml_app

worker/dml_app is an empty folder.  
the real application code is saved in the controller/dml_app.  
the workers read the application code in the controller through NFS, and worker/dml_app is used as the NFS mount path.

## dml_file

conf files are generated by the controller/dml_tool/conf_gen.py, and saved in the controller's dml_file/conf.  
later, conf files will be sent to worker's dml_file/conf.  
log files are generated by workers while running dml_app, and saved in workers' dml_file/log.  
later, log files will be sent to the controller's dml_file/log.