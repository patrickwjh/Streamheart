# Middleware protocol
## General introduction
The connection to the middleware works via Websocket.
Messages are exchanged between client and middleware as JSON objects.

# Applications
### Register
Register your application to receive requests and send events to other clients that connected to 
you. 

### Subscribe
Subscribe your client to existing applications to send requests and receive events from it.

**Predefined applications**
- `middleware`

# Request
Requests are sent by the client and require at least the following fields:

- `application` String: Name to which registered application the message should be sent
- `request-type` String: Name of the request type
- `message-id` int: Client defined identifier for the message, will be echoed in the response

## Response
Once a request is sent, the middleware will return a JSON response with at least the following fields:

- `message-id` int: The client defined identifier specified in the request
- `status` String: Response status, will be one of the following: `ok`, `error`
- `error` String: An error message accompanying an error status

Additional information may be required/returned depending on the request type.

## General request types

### Register
Register your application on the middleware

**Request**

| Name | Type | Description |
|------|:----:|-------------|
| `name` | _String_ | Name of your application |

**Response**

No additional response items.

---
### Unregister
Unregister your application from the middleware. All connect clients will be disconnected.

**Request**

| Name | Type | Description |
|------|:----:|-------------|
| `name` | _String_ | Name of your application |

**Response**

No additional response items.

---
### Subscribe
Subscrie your client to an registered application.

**Request**

| Name | Type | Description |
|------|:----:|-------------|
| `name` | _String_ | Name of the application |

**Response**

No additional response items.

---
### Unsubscribe
Unsubscribe your client from an subscribed application.

**Request**

| Name | Type | Description |
|------|:----:|-------------|
| `name` | _String_ | Name of the application |

**Response**

No additional response items.

# Event
Events are broadcast by the middleware to each subscribed client of an application.

An event message will contain at least the following base field:

- `update-type` String: Type of the event

Additional fields may be present in the event message depending on the event type.

---
### UnsubscribedFrom

Client became unsubscribed from an application

| Name | Type | Description |
|------|:----:|-------------|
| `name` | _String_ | Name of the application |