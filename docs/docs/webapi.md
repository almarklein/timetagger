# TimeTagger public web API



## Introduction

### API base URL

If you run your own instance of TimeTagger, you determine the API endpoint. By default the startup script has it at:

```
    http://localhost/timetagger/api/v2/
```

The API endpoint for the service by [https://timetagger.app](https://timetagger.app) is at:

```
    https://timetagger.app/api/v2/
```

### Authentication

All endpoints in this API need to be authenticated via the `authtoken` field in the request header. This token can be either a web-token (used by the web client), or an api-token (used by 3d party services). A web-token is valid for 14 days, but can be refreshed. An api-token does not expire. Both kinds of tokens can be revoked via the web client. When the authentication of a request fails, a 401 response is given.

### Responses

The server responds with http status code 200 if the request is sound. In this case, the body of the response is always a JSON encoded object.

Otherwise, an appropriate error code is returned, and the body is simply a string with the meaning of that error code and a more specific explanation, e.g. 401 for authentication fails, 404 for invalid API paths, 400 for faulty arguments, etc.

Responses with error code 500 are server errors and should probably be considered a bug.

### Timestamps

All times and timestamps in this document are Unix timestamps (floating point numbers representing the number of seconds since the epoch) unless specified otherwise.



## The endpoints

### GET records

See below for a description of record objects. To get records, the following request can be made:

```
GET ./records?timerange=<timestamp1>-<timestamp2>
```

The timestamps are compared to the record's start and end times (`t1` and `t2`). A record
is included if its partially in the range. If the two timestamps in the range are equal,
it will query all records that include that timestamp. If the range is reversed (`timstamp1 > timestamp2`),
it will query only records that fully occupy that range. Running records are considered
to have their end-time in the infinite future.

The fields in the JSON response:

* `records`: A list of record objects that are (partially) within the range given by the two timestamps.

### PUT records

See below for a description of record objects. To edit records, or submit new records, send a request with a body consisting of a JSON-encoded list of record objects:

```
PUT ./records
```

The fields in the JSON response:

* `accepted`: The keys of the accepted records.
* `failed`: The keys of the rejected records.
* `errors`: The error messages corresponding to the items in `fail`, plus possibly additional error messages.

### GET settings

See below for a description of settings objects. To get all settings, perform the following request:

```
GET ./settings
```

The fields in the JSON response:

* `settings`: a list of settings objects.

### PUT settings

Settings can be updated by doing a request with a body consisting of a JSON-encoded list of settings objects.

```
PUT ./settings
```

The fields in the JSON response:

* `accepted`: The keys of the accepted settings.
* `failed`: The keys of the rejected settings.
* `errors`: The error messages corresponding to the items in `fail`, plus possibly additional error messages.

### GET updates

Clients can cache the records and settings locally and efficiently get updates. Such clients have access to all the data, while also being up-to-date. The web client uses this approach (it never uses `GET records`).

```
GET ./updates?since=<timestamp>
```

The fields in the JSON response:

* `server_time`: a timestamp indicating the time of the server when the update was sampled. The client should use this value in the `since` field of
  the next update request.

* `reset`: either 0 or 1, indicating whether the client should purge its local cache. This will rarely be 1, but it can happen, e.g. in the event that a database is reset from backup.
* `records`: a list of record objects that have changed since. Can be empty.
* `settings`: a list of settings objects that have changed since. Can be empty.

### Other endpoints

If you look at the [source code](https://github.com/almarklein/timetagger/blob/main/timetagger/server/_apiserver.py), you'll see a few other endpoints, e.g. to refresh the web-token and obtain the api-token. These two endpoints are only available with a web-token (not with an api-token).

Further, the API at [https://timetagger.app](https://timetagger.app) has endpoints to obtain information about the subscription. These endpoints are currently not document and should not be considered public. This may change in the future.

If you implement your own TimeTagger server, you may of course support additional endpoints.



## Object shapes

### Record objects

Records are objects/dicts with the following fields:

* `key`: a unique string identifier for this record. When creating new record, it is the responsibility of the client to generate this key with a good random generator.
* `t1`: the record start time as an integer Unix timestamp.
* `t2`: the record stop time as an integer Unix timestamp.
* `ds`: the record description (can be empty).
* `mt`: the modified time (set by the client).
* `st`: the server time (set by the server when storing a record). Clients should set this to 0.0 for new records.

### Settings objects

Settings are objects/dicts with the following fields:

* `key`: a unique string identifier for this setting. This should usually just be the settings name. If you want to submit new settings (e.g. for a new/custom client) consider using a prefix to avoid name conflicts.
* `value`: the value of this setting. This must be a JSON compatible object.
* `mt`: the modified time (set by the client).
* `st`: the server time (set by the server when storing a record). Clients should set this to 0.0 for new records.


### Deleting records

Records cannot be deleted from the server's point of view. But by
convention, records that have a `ds` (description) starting with
"HIDDEN" are considered deleted by the client. Both the TimeTagger web
client and CLI api honor this convention.


### Syncing and eventual consistency

The `mt` (modified time) is set by a client when updating a record. This value is used to determine what object is older, in case two clients both update the same record. Note that client's clock can differ.

The `st` (server time) may only be set by the server (clients should initialize it with 0.0). The server guarantees that each update to an object results in a higher `st`.

When clients that use `GET updates` (i.e. have a local cache) process incoming records, they should compare `st` when both records have an `st > 0`, and otherwise compare the `mt` values. If clients follow these rules, the system will be eventually consistent.
