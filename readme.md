# swagger_apib_gen

+ Auto generate swagger and apib restful api document

### Usage

+ `gen_swagger`

```bash
python3 gen_swagger.py -m main.go -o swag.yaml -e go
```

```
usage: gen_swagger.py [-h] -m MAIN -o OUTPUT [-e [EXT [EXT ...]]]

optional arguments:
  -h, --help                                   show this help message and exit
  -m MAIN, --main MAIN                         path of main file containing swagger config
  -o OUTPUT, --output OUTPUT                   path of output yaml
  -e [EXT [EXT ...]], --ext [EXT [EXT ...]]    extensions of files wanted to parse
```

+ `gen_swagger_html`

```bash
python3 gen_swagger_html.py -i swag.yaml -o swag.html
```

```
usage: gen_swagger_html.py [-h] -i INPUT -o OUTPUT

optional arguments:
  -h, --help                   show this help message and exit
  -i INPUT, --input INPUT      path of input yaml file
  -o OUTPUT, --output OUTPUT   path of output html file
```

### Annotaton

+ main

```go
// @Title                   vid backend
// @Version                 1.1
// @Description             Backend of repo https://github.com/vidorg/vid_vue
// @TermsOfService          https://github.com/vidorg
// @Host                    localhost:3344
// @BasePath                /
// @License.Name            MIT
// @License.Url             https://github.com/vidorg/vid_backend/blob/master/LICENSE
// @Contact.Name            xxx
// @Contact.Url             xxx
// @Contact.Email           xxx

// @DemoResponse            ./src/model/dto/Demo.json
// @Authorization.Param     Authorization header string true "User login token"
// @Authorization.Error     401 authorization failed
// @Authorization.Error     401 token has expired
```

+ controller

```go
// @Router              /v1/user/{uid}/subscriber [GET]
// @Summary             User's subscribers
// @Description         Query user's subscribers, return page data
// @Tag                 User
// @Tag                 Subscribe
// @Param               uid path integer true "user id"
// @Param               page query integer false "page"
// @Accept              multipart/form-data
// @ErrorCode           400 request param error
// @ErrorCode           404 user not found
/* @Response 200        {
                            "code": 200,
                            "message": "success",
                            "data": {
                                "count": 1,
                                "page": 1,
                                "data": [ ${user} ]
                            }
                        } */
/* @Response 400        {
                            "code": 200,
                            "message": "request param error"
                        } */

// @Router              /v1/user/subscribing [PUT] [Auth]
// @Summary             Subscribe user
// @Description         Subscribe someone
// @Tag                 User
// @Tag                 Subscribe
// @Param               to formData integer true "user id"
// @Accept              multipart/form-data
// @Produce             application/json
// @ErrorCode           400 request param error
// @ErrorCode           400 request format error
// @ErrorCode           404 user not found
// @ErrorCode           500 subscribe failed
/* @Response 200        {
                            "code": 200,
                            "message": "success"
                        } */
```

### References

+ [How can I control what scalar form PyYAML uses for my data?](https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data)
