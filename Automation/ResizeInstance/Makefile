TARGET_DIR = "./Output"

documents: targetdir createdocuments
	@echo "Done making documents"

targetdir:
	@echo "Making $(TARGET_DIR)"
	mkdir -p ./Output

createdocuments:
	python ./Setup/create_document.py > ./Output/aws-ResizeInstance.json

test: documents
	python -m unittest discover Tests

clean:
	@echo "Removing $(TARGET_DIR)"
	@rm -rf ./Output