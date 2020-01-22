package main

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
							"message": "success",
							"data": ${array}
 						} */
func swagger() {

}

// @Router              /v1/user/subscribing [PUT] [Auth]
// @Summary             Subscribe user
// @Description         Subscribe someone
// @Tag                 User
// @Param               to formData integer true "user id"
// @ErrorCode           400 request param error
// @ErrorCode           400 request format error
// @ErrorCode           404 user not found
// @ErrorCode           500 subscribe failed
/* @Request 200         {|
							"Content-Type": "application/json",
							"Authorization": "xxx"
						|} {
							"to": 2
 						} */
/* @Response 200        {| "Content-Type": "application/json; charset=utf-8" |}
						{
							"code": 200,
							"message": "success"
 						} */
/* @Request 400         {|
							"Content-Type": "application/json",
							"Authorization": "xxx"
 						|} */
/* @Response 400        {| "Content-Type": "application/json; charset=utf-8" |}
						{
							"code": 400,
							"message": "request param error"
 						} */
/* @Response 500        {
							"code": 500,
							"message": "subscribe failed"
 						} */
func apib() {

}
