
echo Generating swagger yaml...
python3 gen_swagger.py -m ./demo/swag/main.go -o ./demo/swagger.yaml -e go

echo 
echo Generating swagger html...
python3 gen_swagger_html.py -i ./demo/swagger.yaml -o ./demo/swagger.html
