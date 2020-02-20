package main

// @Model         LoginParam
// @Description   body of login param
// @Property      username string                                  true  "username"     (example:ExampleUsername)
// @Property      password string                                  true  "password"     (example:ExamplePassword)
// @Property      expire   integer                                 false "login expire" (example:86400)
// @Property      other    object(#LoginParamRef)                  false "other param"
// @Property      others   array(#LoginParamRef)                   false "other param"
// @Property      enum     string(enum:a,2,3\,4)                   false "other param"
// @Property      enum2    integer(enum:5,6,7,8)(format:integer32) false "other param"
// @Property      format   string(format:2000-01-01 00:00:00)      false "other param"

// @Model         LoginParamRef
// @Description   ref used
// @Property      other string false "other param"

// @Model         Result
// @Description   global result model
// @Property      code    integer true "status code"    200
// @Property      message string  true "status message" success
