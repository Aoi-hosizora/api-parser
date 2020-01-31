# swagger_apib_gen

+ Auto generate swagger2 and apib restful api document
+ **Apib generator isn't under maintenance**

## Dependence

+ `jsonref 0.2` (`json` module don't support `$ref` json)

## Usage

+ Usage in project see [vidorg/vid_backend](https://github.com/vidorg/vid_backend)

+ `gen_swagger`

```bash
python3 gen_swagger.py -m ./demo/swag/main.go -o ./demo/swagger.yaml -e go
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
python3 gen_swagger_html.py -i ./demo/swagger.yaml -o ./demo/swagger.html
```

```
usage: gen_swagger_html.py [-h] -i INPUT -o OUTPUT
optional arguments:
  -h, --help                   show this help message and exit
  -i INPUT, --input INPUT      path of input yaml file
  -o OUTPUT, --output OUTPUT   path of output html file
```

+ `gen_apib`

```bash
python3 gen_apib.py -m ./demo/apib/main.go -o ./demo/apiary.apib -e go
```

```
usage: gen_apib.py [-h] -m MAIN -o OUTPUT [-e [EXT [EXT ...]]]
optional arguments:
  -h, --help                                   show this help message and exit
  -m MAIN, --main MAIN                         path of main file containing swagger config
  -o OUTPUT, --output OUTPUT                   path of output yaml
  -e [EXT [EXT ...]], --ext [EXT [EXT ...]]    extensions of files wanted to parse
```

## Annotaton

+ See [main.go](https://github.com/Aoi-hosizora/swagger_apib_gen/blob/master/demo/main.go) and [ctrl.go](https://github.com/Aoi-hosizora/swagger_apib_gen/blob/master/demo/ctrl.go)

### Main File Format

+ Meta data (only single annotation)

```go
// @Title
// @Version
// @Description
// @TermsOfService
// @Host
// @BasePath
// @License.Name
// @License.Url
// @Contact.Name
// @Contact.Url
// @Contact.Email
```

+ Tag (multiple)

```go
// @Tag User      "User-Controller"
// @Tag Subscribe "Sub-Controller"
// @Tag $tag      "$description"
```

+ DemoModel (single)
    + see [Demo Model](#demo-model)

```go
// @DemoModel ./demo/demo.json
// @DemoModel $jsonPath
```

+ GlobalSecurity (multiple) 
    + only support `apiKey`

```go
// @GlobalSecurity Jwt   Authorization header
// @GlobalSecurity $name $field        $in
```

+ Template (multiple)
    + only support `@Param` `@ResponseDesc` `@ResponseHeader` `@Response`

```go
// @Template Auth.ResponseDesc 401 unauthorized user
// @Template Page.Param        other header integer false false "other header"
// @Template $name.$annotation $content
```

### Controller File Format

+ Meta data (single)

```go
// @Router      xxx/{id}/xxx [GET]
// @Summary     xxx
// @Description xxx
```

+ Tag (multiple)

```go
// @Tag User
// @Tag Subscribe
// @Tag $tag
```

+ Param (multiple)
    + `in`: `query` `path` `header` `body` `formData`
    + `type`: `string` `integer` `number(float32)` `boolean` `#xxx`
    + `allowEmptyValue: *` means not set `allowEmptyValue` value
    + See [Param Type](https://github.com/swaggo/swag#param-type) and [Data Type](https://github.com/swaggo/swag#data-type) 

```go
// @Param uid   formData integer        true      false            "user id"    1
// @Param param body     #LoginParam    true      false            "loginParam"
// @Param $name $in      $type          $required $allowEmptyValue "$comment"   ($default)
```

+ Template (single)

```go
// @Template Auth   Page
// @Template $name1 $name2 $name3
```

+ Security (multiple)

```go
// @Security Jwt
// @Security $name
```

+ Accept & Produce (multiple)
    + `application/json` `multipart/form-data` `text/xml` `text/plain` `text/html`
    + see [Mime Types](https://github.com/swaggo/swag#mime-types)

```go
// @Accept  multipart/form-data
// @Produce application/json
// @Accpet  $mimeType
// @Produce $mimeType
```

+ ResponseDesc (multiple)

```go
// @ResponseDesc 400   request param error
// @ResponseDesc 401   unauthorized user
// @ResponseDesc $code $content
```

+ ResponseHeader (single)

```go
// @ResponseHeader 200   {"Content-Type": "application/json; charset=utf-8" }
// @ResponseHeader $code $json
```

+ ResponseModel (single)

```go
// @ResponseModel  200   #Result
// @ResponseModel  $code $mdoel
```

+ Response (single)

```go
/* @Response 200    { 
                        "code": 200, 
                        "message": "success"
                    } */
// @Response $code $json
```

### Model File Format

+ Meta data (single)

```go
// @Model
// @Description
```

+ Property (mutiple)
    + `allowEmptyValue: *` means not set `allowEmptyValue` value

```go
// @Property username string                 true      false            "username"     ExampleUsername
// @Property expire   integer                false     true             "login expire" 86400
// @Property other    object(#LoginParamRef) false     true             "other param"
// @Property others   array(#LoginParamRef)  false     true             "other param"
// @Property $name    $type($model)          $required $allowEmptyValue $description   ($example)
```

### Type Format

+ Param

```go
// @Param xxx integer
// @Param xxx string

// @Param xxx #Result
// @Param xxx #Param

// @Param xxx string(enum:a,2,3\,4) -> {"a", "2", "3,4"}
// @Param xxx integer(enum:1,2,3,4) -> {1, 2, 3, 4}
```

+ Model

```go
// @Property xxx integer
// @Property xxx string

// @Property xxx object(#Param)
// @Property xxx array(#Param)

// @Property xxx string(enum:a,2,3\,4)
// @Property xxx integer(enum:1,2,3,4)(format:integer32)
// @Property xxx string(format:2000-01-01 00:00:00)
```

+ ResponseModel

```go
// @ResponseModel 200 #UserDto
```

### Demo Model

+ Support `$ref` type of json in `@ResponseDesc` `@ResponseHeader` `@Response`

```json
{
    "resp_success": {
        "code": 200,
        "message": "success"
    },
    "resp_data": {
        "code": 200,
        "message": "success",
        "data": {
            "$ref": "#/$models/some-data"
        }
    },
    "resp_datas": {
        "code": 200,
        "message": "success",
        "data": [
            {
                "$ref": "#/$models/some-data"
            }
        ]
    },
    "$models": {
        "base": {
            "base-field": "base-value"
        },
        "some-data": {
            "field1": "value1",
            "field2": "value2",
            "field3": {
                "$ref": "#/$models/base"
            }
        }
    }
}
```

### References

+ [How can I control what scalar form PyYAML uses for my data?](https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data)
+ [JSON Reference](https://json-spec.readthedocs.io/reference.html)
+ [gazpachoking/jsonref](https://github.com/gazpachoking/jsonref)
+ [Python how convert single quotes to double quotes to format as json string](https://stackoverflow.com/questions/47659782/python-how-convert-single-quotes-to-double-quotes-to-format-as-json-string/55739462#55739462)
+ [OpenAPI 2 Adding Examples](https://swagger.io/docs/specification/2-0/adding-examples/)