package main

// @Router              /v1/user/{uid}/subscriber [GET]
// @Summary             User's subscribers
// @Description         Query user's subscribers, return page data
// @Tag                 User
// @Tag                 Subscribe
// @Param               uid path integer true false "user id" 1
// @Param               page query integer false true "page" 1
// @Accept              multipart/form-data
// @RequestHeader 200   {"a": "b"}
// @RequestEx 200       {"c": "d", "e": "f"}
// @ResponseDesc 400    "request param error"
// @ResponseDesc 404    "user not found"
// @ResponseEx 200      ${resp_user}
// @ResponseHeader 200  {"a": "b"}
/* @ResponseEx 400      {
							"code": 400,
							"message": "request param error"
 						} */

// @Router              /v1/user/subscribing [PUT]
// @Template            Auth Other
// @Summary             Subscribe user
// @Description         Subscribe someone
// @Tag                 User
// @Tag                 Subscribe
// @Param               to formData integer true false "user id"
// @Param               to2 formData integer(enum:1,2,3) true false "user id"
// @Accept              multipart/form-data
// @Produce             application/json
// @RequestHeader 200   {"a": "b"}
// @RequestEx 200       {"c": "d", "e": "f"}
// @ResponseDesc 400    "request param error"
// @ResponseDesc 400    "request format error"
// @ResponseDesc 404    "user not found"
// @ResponseDesc 500    "subscribe failed"
/* @ResponseEx 200      {
							"code": 200,
							"message": "success",
							"data": ${array}
 						} */
func func1() {

}

// @Router              /v1/user/subscribing [DELETE]
// @Template            Auth
// @Summary             Unsubscribe user
// @Tag                 User
// @Param               to formData integer true false "user id"
// @ResponseDesc 400    "request param error"
// @ResponseDesc 400    "request format error"
// @ResponseDesc 404    "user not found"
// @ResponseDesc 500    "unsubscribe failed"
// @ResponseHeader 200  { "Content-Type": "application/json; charset=utf-8" }
/* @ResponseModel 200   #Result */
// @ResponseHeader 400  { "Content-Type": "application/json; charset=utf-8" }
/* @ResponseEx 400      {
							"code": 400,
							"message": "request param error"
 						} */
/* @ResponseModel 400 	#Result */
/* @ResponseEx 500      {
							"code": 500,
							"message": "unsubscribe failed"
 						} */
/* @ResponseModel 500 	#Result */
func func2() {

}

// @Router           /v1/auth/login [POST]
// @Summary          Login
// @Tag              Authorization
// @Param            param body #LoginParam true false "login param"
// @ResponseDesc     200 "OK"
/* @ResponseEx 200   ${resp_user} */
func func3() {

}
