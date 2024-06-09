cd cloud_functions
poetry build
cp ../../dist/op_tcg-0.1.0.tar.gz .
cat > requirements.txt << EOF
op_tcg-0.1.0.tar.gz
functions-framework
google-cloud-pubsub
scrapy
EOF
zip -r function-source.zip main.py requirements.txt op_tcg-0.1.0.tar.gz $new_tmp_file
cd ..
terraform apply