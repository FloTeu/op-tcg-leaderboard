cd cloud_functions
poetry build
cp ../../dist/op_tcg-0.1.0.tar.gz .
cat > requirements.txt << EOF
op_tcg-0.1.0.tar.gz
functions-framework
EOF
export new_tmp_file=$((1 + $RANDOM % 10)).py
touch $new_tmp_file
zip -r function-source.zip main.py requirements.txt op_tcg-0.1.0.tar.gz $new_tmp_file
rm $new_tmp_file
cd ..
terraform apply