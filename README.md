# api-parser

+ A command lint tool for rest api to generating swagger2 and apib document

## Dependence

+ `jsonref 0.2` (`json` module don't support `$ref` json)

## Build

```bash
pyinstaller -F cli.py
# or
# python "\Python36\Scripts\pyinstaller-script.py" -F cli.py -n apiparser.exe
```

## Usage

```bash
cli.exe \
    -y \                    # do yaml               (store_true)
    -m main.go \            # main setting file
    -d . \                  # root directory
    -o a.yaml \             # output yaml name
    -e go \                 # extensions
    -c \                    # need content-type     (store_true)
    -s \                    # do generate swagger   (store_true)
    --swag_output a.html \  # output html name
    -a \                    # do generate apib      (store_true)
    --apib_output a.apib    # output apib name
```

## Annotation

### Main File Format

+ Meta data (only single annotation)

```go
// @Title            (required)
// @Version          (required)
// @Description      (required)
// @TermsOfService   
// @Host             (required)
// @BasePath         (required)
// @License.Name     
// @License.Url      
// @Contact.Name     
// @Contact.Url      
// @Contact.Email    
```

+ Tag (multiple) (not required)

```go
// @Tag User      "User-Controller"
// @Tag Subscribe "Sub-Controller"
// @Tag $tag      "$description"
```

+ DemoModel (single) (not required)
    + see [Demo Model](#demo-model)

```go
// @DemoModel ./demo/demo.json
// @DemoModel $jsonPath
```

+ GlobalSecurity (multiple) (not required)
    + only support `apiKey` now

```go
// @GlobalSecurity Jwt   Authorization header
// @GlobalSecurity $name $field        $in
```

+ Template (multiple) (not required)
    + only support:
    + `@Param`
    + `@RequestHeader` `@RequestEx`
    + `@ResponseDesc` `@ResponseHeader` `@ResponseModel` `@ResponseEx`

```go
// @Template Auth.ResponseDesc 401 unauthorized user
// @Template Page.Param        other header integer false false "other header"
// @Template $name.$annotation $content
```

### Controller File Format

+ Meta data (single)

```go
// @Router      xxx/{id}/xxx [GET]   (required)
// @Summary     xxx                  (required)
// @Description xxx                  
```

+ Tag (multiple) (not required)

```go
// @Tag User
// @Tag Subscribe
// @Tag $tag
```

+ Param (multiple) (not required)
    + `in`: `query` `path` `header` `body` `formData`
    + `type`: `string` `integer` `number(float32)` `boolean` `#xxx`
    + `allowEmptyValue: *` means not set `allowEmptyValue` value
    + See [Param Type](https://github.com/swaggo/swag#param-type) and [Data Type](https://github.com/swaggo/swag#data-type) 

```go
// @Param uid   formData integer     true      "user id"    (example:2)  (default:1)
// @Param uid2  formData integer     true      "user id"    (empty:true) (default:1) (example:2)
// @Param param body     #LoginParam true      "loginParam" (empty:false)
// @Param $name $in      $type       $required "$comment"   ($empty)($default)($example)
```

+ Template (single) (not required)

```go
// @Template Auth   Page
// @Template $name1 $name2 $name3
```

+ Security (multiple) (not required)

```go
// @Security Jwt
// @Security $name
```

+ Accept & Produce (multiple) (not required)
    + `application/json` `multipart/form-data` `text/xml` `text/plain` `text/html`
    + see [Mime Types](https://github.com/swaggo/swag#mime-types)

```go
// @Accept  multipart/form-data
// @Produce application/json
// @Accept  $mimeType
// @Produce $mimeType
```

+ RequestHeader (single) (not required)

```go
// @RequestHeader 200   {"Content-Type": "application/json" }
// @RequestHeader $code $json
```

+ RequestEx (single) (not required)

```go
// @RequestEx 200   {"to": 1, "status": "ok"}
// @RequestEx $code $json
```

+ ResponseDesc (multiple) (not required)

```go
// @ResponseDesc 400   request param error
// @ResponseDesc 401   unauthorized user
// @ResponseDesc $code $content
```

+ ResponseHeader (single) (not required)

```go
// @ResponseHeader 200   {"Content-Type": "application/json; charset=utf-8" }
// @ResponseHeader $code $json
```

+ ResponseModel (single) (not required)

```go
// @ResponseModel  200   #Result
// @ResponseModel  $code $model
```

+ ResponseEx (single) (not required)

```go
/* @ResponseEx 200  { 
                        "code": 200, 
                        "message": "success"
                    } */
// @ResponseEx $code $json
```

### Model File Format

+ Meta data (single)

```go
// @Model         (required)
// @Description   (required)
```

+ Property (multiple) (not required)

```go
// @Property username string                 true      "username"     (empty:false) (example:ExampleUsername)
// @Property expire   integer                false     "login expire" (empty:true)  (example:86400)
// @Property other    object(#LoginParamRef) false     "other param"
// @Property others   array(#LoginParamRef)  false     "other param"  (empty:false)
// @Property $name    $type($model)          $required $description   ($empty)($example)
```

### Type Format

+ Model property / parameter
    + After type: `(enum:xx)` `(format:xx)`
    + After desc: `(empty:true)` `(example:xx)` `(default:xx)`
    + `@Param xxx string(enum:a,b,c)(format:test) "xxx parameter" (empty:false)(example:a)(default:a)`

+ Param (`#Obj`)

```go
// @Param xxx integer
// @Param xxx string

// @Param xxx #Result
// @Param xxx #Param

// @Param xxx string(enum:a,2,3\,4) -> {"a", "2", "3,4"}
// @Param xxx integer(enum:1,2,3,4) -> {1, 2, 3, 4}
```

+ ResponseModel (`#Obj`)

```go
// @ResponseModel 200 #UserDto
```

+ Model (`object(#Obj) \ array(#Obj)`)

```go
// @Property xxx integer
// @Property xxx string

// @Property xxx object(#Param)
// @Property xxx array(#Param)

// @Property xxx string(enum:a,2,3\,4)
// @Property xxx integer(enum:1,2,3,4)(format:integer32)
// @Property xxx string(format:2000-01-01 00:00:00)
```

### Demo Model

+ Support `$ref` type of json in `@RequestHeader` `@RequestEx` `@ResponseDesc` `@ResponseHeader` `@ResponseEx`

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
+ [albertosottile/py2exe](https://github.com/albertosottile/py2exe)
