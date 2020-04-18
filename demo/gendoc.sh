echo Generating swagger yaml...
python3 yaml.py \
    -m ./demo/swag/main.go \
    -s ./demo/swag/ \
    -o ./demo/swagger.yaml \
    -e go

echo 
echo Generating swagger html...
python3 swagger.py \
    -i ./demo/swagger.yaml \
    -o ./demo/swagger.html

echo 
echo Generating apiary yaml...
python3 yaml.py \
    -m ./demo/apib/main.go \
    -s ./demo/apib/ \
    -n true \
    -o ./demo/apiary.yaml \
    -e go

echo 
echo Generating apiary apib...
python3 apib.py \
    -i ./demo/apiary.yaml \
    -o ./demo/apiary.apib
