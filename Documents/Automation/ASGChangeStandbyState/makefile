
TARGET_DIR = "./Output"

documents: targetdir createdocuments
	@echo "Done making documents"

targetdir:
	@echo "Making $(TARGET_DIR)"
	mkdir -p ./Output

createdocuments:
	python ./Setup/create_document.py EnterStandby > ./Output/aws-ASGEnterStandby.json
	python ./Setup/create_document.py ExitStandby > ./Output/aws-ASGExitStandby.json

test: documents
	python -m unittest discover Tests
	#python -m unittest Tests.tests.TestCase.test_enter_standby_document
	#python -m unittest Tests.tests.TestCase.test_exit_standby_document

clean:
	@echo "Removing $(TARGET_DIR)"
	@rm -rf ./Output
