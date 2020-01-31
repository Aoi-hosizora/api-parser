package main

// @Model         LoginParam
// @Description   body of login param
// @Property      username string                 true  false "username"     ExampleUsername
// @Property      password string                 true  false "password"     ExamplePassword
// @Property      expire   integer                false true  "login expire" 86400
// @Property      other    object(#LoginParamRef) false true  "other param"
// @Property      others   array(#LoginParamRef)  false true  "other param"
// @Property      enum     string(enum:a,2,3\,4)  false true  "other param"
// @Property      enum2    integer(enum:5,6,7,8)  false true  "other param"

// @Model         LoginParamRef
// @Description   ref used
// @Property      other string false true "other param"

// @Model         Result
// @Description   global result model
// @Property      code    integer true false "status code"    200
// @Property      message string  true false "status message" success
