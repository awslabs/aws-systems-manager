
TARGET_DIR = "./Output"

documents: targetdir escapeddocuments copydocuments
	@echo "Done making documents"

targetdir:
	@echo "Making $(TARGET_DIR)"
	@test ! -d $(TARGET_DIR) && mkdir $(TARGET_DIR)

escapeddocuments: installmodules
	python ./createdocument.py 

installmodules:
	@echo "Installing Python module escapejson"
	pip install escapejson

copydocuments:
	@echo "Copying automation documents"
	cp ./Documents/awstest-CreateManagedInstanceWindows.json ./Output
	cp ./Documents/awstest-CreateManagedInstanceLinux.json ./Output 

clean:
	@echo "Removing $(TARGET_DIR)"
	@rm -rf ./Output
