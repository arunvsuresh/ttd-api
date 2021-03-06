import logging
import json
import requests
import datetime


class Base(dict):

    connection = None

    # Needs to be defined in the subclass
    obj_name = None

    def __init__(self, connection):
        self.logger = logging.getLogger("ttd-api")
        Base.connection = connection
        super(Base, self).__init__()

    def log(self, level, message):
        rval = None
        try:
            # make sure we remove non-ascii chars and trim the message to 1000 chars
            message = message.encode('ascii', 'ignore')[:1000]
            rval = self.logger.log(level, message)
        except:
            pass

        return rval

    def get_url(self):
        return "{0}/{1}".format(Base.connection.url, self.obj_name)

    def get_create_url(self):
        return self.get_url()

    def get_find_url(self, id):
        return "{0}/{1}".format(self.get_url(), id)

    def find(self, id=None):
        if id is None:
            response = self._execute("GET", self.get_url(), None)

            rval = []
            if response:
                rval = self._get_response_objects(response)
            return rval
        else:
            response = self._execute("GET", self.get_find_url(id), None)

            if response:
                return self._get_response_object(response)
            else:
                return None

    def create(self):
        if id in self:
            del self['id']

        print "CREATING"
        response = self._execute("POST", self.get_create_url(), json.dumps(self.export_props()))
        obj = self._get_response_object(response)
        self.import_props(obj)

        return self.getId()

    def getId(self):
        return self.get('id')

    def save(self):
        if self.getId() is None or self.getId() == 0:
            raise Exception("cant update an object with no id")

        response = self._execute("PUT", self.get_url(), json.dumps(self.export_props()))
        obj = self._get_response_object(response)
        self.import_props(obj)

        return self.getId()

    def _execute(self, method, url, payload):
        return self._execute_no_reauth(method, url, payload)

    def _execute_no_reauth(self, method, url, payload):
        headers = Base.connection.get_authorization()

        headers['Content-Type'] = 'application/json'

        start_time = datetime.datetime.now()
        curl_command = ""
        rval = None
        if method == "GET":
            curl_command = "curl -H 'Content-Type: application/json' -H 'TTD-Auth: {0}' '{2}'".format(headers['TTD-Auth'], payload, url)
            rval = requests.get(url, headers=headers, data=payload, verify=False)
        elif method == "POST":
            curl_command = "curl -XPOST -H 'Content-Type: application/json' -H 'TTD-Auth: {0}' -d '{1}' '{2}'".format(headers['TTD-Auth'], payload, url)
            rval = requests.post(url, headers=headers, data=payload, verify=False)
        elif method == "PUT":
            curl_command = "curl -XPUT -H 'Content-Type: application/json' -H 'TTD-Auth: {0}' -d '{1}' '{2}'".format(headers['TTD-Auth'], payload, url)
            rval = requests.put(url, headers=headers, data=payload, verify=False)
        elif method == "DELETE":
            curl_command = "curl -XDELETE -H 'Content-Type: application/json' -H 'TTD-Auth: {0}' '{2}'".format(headers['TTD-Auth'], payload, url)
            rval = requests.delete(url, headers=headers, verify=False)
        else:
            raise Exception("Unknown method")
        
        end_time = datetime.datetime.now()
        total_time = end_time - start_time
        self.log(logging.DEBUG, "{0}, \"{1}\"".format(str(total_time), curl_command.replace('"', '""')))
        return rval

    def _get_response_objects(self, response):
        rval = []
        obj = json.loads(response.text)
        if obj and 'Result' in obj:
            results = obj.get('Result')
            for result in results:
                new_obj = self.__class__(Base.connection)
                new_obj.import_props(result)
                rval.append(new_obj)
        else:
            self.log(logging.ERROR, "-1, \"{0}\"".format(response.text))
            raise Exception("Bad response code {0}".format(response.text))

        return rval

    def _get_response_object(self, response):
        obj = json.loads(response.text)
        new_obj = None
        if obj and response.status_code == 200:
            new_obj = self.__class__(Base.connection)
            new_obj.import_props(obj)
        else:
            self.log(logging.ERROR, "-1, \"{0}\"".format(response.text))
            raise Exception("Bad response code {0}".format(response.text))

        return new_obj

    def import_props(self, props):
        for key, value in props.iteritems():
            self[key] = value

    def export_props(self):
        rval = {}
        # do this an obvious way because using __dict__ gives us params we dont need.
        for key, value in self.iteritems():
            rval[key] = value

        return rval
