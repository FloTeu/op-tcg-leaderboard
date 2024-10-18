cd cloud_functions
poetry build
export version=$(poetry version -s)
cp ../../dist/op_tcg-$version.tar.gz .
cat > requirements.txt << EOF
op_tcg-$version.tar.gz
functions-framework
google-cloud-pubsub
scrapy
EOF
rm -f function-source.zip
zip -r function-source.zip main.py requirements.txt op_tcg-$version.tar.gz
cd ..
terraform apply -auto-approve