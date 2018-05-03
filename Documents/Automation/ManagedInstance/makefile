
TARGET_DIR = "./Output"

documents: targetdir createdocuments
	@echo "Done making documents"

targetdir:
	@echo "Making $(TARGET_DIR)"
	mkdir -p ./Output

createdocuments:
	python ./Setup/create_document.py windows main > ./Output/aws-CreateManagedWindowsInstance.json
	python ./Setup/create_document.py linux main > ./Output/aws-CreateManagedLinuxInstance.json
	python ./Setup/create_document.py windows approve > ./Output/aws-CreateManagedWindowsInstanceWithApproval.json
	python ./Setup/create_document.py linux approve > ./Output/aws-CreateManagedLinuxInstanceWithApproval.json

test: documents
	python -m unittest discover Tests
	# python -m unittest Tests.test_ami_info.AmiInfoTest.test_handler_on_create_windows

clean:
	@echo "Removing $(TARGET_DIR)"
	@rm -rf ./Output
