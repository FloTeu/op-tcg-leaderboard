cd cloud_functions
poetry build
cp ../../dist/op_tcg-0.1.0.tar.gz .
cat > requirements.txt << EOF
op_tcg-0.1.0.tar.gz
functions-framework
EOF
zip -r function-source.zip main.py requirements.txt op_tcg-0.1.0.tar.gz
cd ..
