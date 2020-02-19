echo Generating swagger yaml...
python3 gen_yaml.py -m ./demo/swag/main.go -s ./demo/swag/ -o ./demo/swagger.yaml -e go

echo 
echo Generating swagger html...
python3 gen_swagger.py -i ./demo/swagger.yaml -o ./demo/swagger.html

echo 
echo Generating apiary yaml...
python3 gen_yaml.py -m ./demo/apib/main.go -s ./demo/apib/ -o ./demo/apiary.yaml -e go

echo 
echo Generating apiary html...
python3 gen_swagger.py -i ./demo/apiary.yaml -o ./demo/apiary.apib
