import socket
import stat
import datetime
from pathlib import Path

import requests
import os
import argparse
from threading import Thread


class ClientRequestThread(Thread):
    def __init__(self, port, host, request_file, root_dir):
        '''
        :param port: port number on which app runs
        :param host: default value is localhost
        :param request_file: Client requested file
        :param root_dir: directory on which all the necessary files exist
        '''
        Thread.__init__(self)
        self.PORT = port
        self.HOST = host
        self.request_file = request_file
        self.root_dir = root_dir
        self.path = ''
        self.response = None
        self.status_code = ''
        self.thread_header = ''
        print("New Thread created to handle a request %s at %s:%s" %(request_file,  host,port))

    def run(self):
        '''
        Thread's main functionality
        Check's for the request type and serves the request based on factors like
        availability of file, validity of the request and accessibility to the file.
        :return: None
        '''
        self.request_file = self.request_file.lstrip('/')
        if self.request_file == '' or self.request_file == 'favicon.ico':
            self.request_file = 'index.html'  # Load index file as default
        self.path = self.root_dir + self.request_file
        try:
            # Download file and then render them
            if self.request_file != 'index.html':
                check_file_exists = Path(self.path)
                if not check_file_exists.is_file():
                    self.status_code = download_files(self.request_file, self.path)
                    if self.status_code != 200:
                        raise Exception()

            # Check if client has access to request for the given file if not pass 403
            if is_group_readable(self.path):
                read_file = open(self.path, 'rb')
                self.response = read_file.read()
                read_file.close()
                file_length = os.path.getsize(self.path)
                self.thread_header = 'HTTP/1.1 200 OK\n'
                mime_type = get_content_type(self.request_file)
                self.thread_header += 'Content-Type: ' + str(mime_type) + '\n'
                self.thread_header += 'Content-Length: ' + str(file_length) + '\n'
            else:
                self.status_code = 403
                raise Exception()

        except Exception as e:
            # serve 400 status code
            if self.status_code == 400 or self.status_code == "" :
                self.thread_header = 'HTTP/1.1 400 Bad Request\n'
                self.thread_header += 'Content-Type: ' + '' + '\n'
                self.thread_header += 'Content-Length: ' + str(0) + '\n'
                self.response = '<html><body><center><h3>Error 400: Bad Request</h3><p>Python HTTP ' \
                                'Server</p></center></body></html>'.encode('utf-8')
            # serve 403 status code
            elif self.status_code == 403:
                self.thread_header = 'HTTP/1.1 403 Permission denied\n'
                self.thread_header += 'Content-Type: ' + '' + '\n'
                self.thread_header += 'Content-Length: ' + str(0) + '\n'
                self.response = '<html><body><center><h3>Error 403: Permission denied</h3><p>Python HTTP ' \
                                'Server</p></center></body></html>'.encode('utf-8')

            # serve 404 status code
            elif self.status_code == 404:
                self.thread_header = 'HTTP/1.1 404 Not Found\n'
                self.thread_header += 'Content-Type: ' + '' + '\n'
                self.thread_header += 'Content-Length: ' + str(0) + '\n'
                self.response = '<html><body><center><h3>Error 404: Not Found</h3><p>Python HTTP ' \
                                'Server</p></center></body></html>'

        finally:
            # After checking all factors send the header to notify client
            self.thread_header += 'Date: ' + str(datetime.datetime.now()) + '\n\n'
            print("HEADERS:", self.thread_header)
            final_response = self.thread_header.encode('utf-8')
            if isinstance(self.response, str):
                self.response = self.response.encode('utf-8')
            final_response += self.response
            connection.send(final_response)
            connection.close()


def is_group_readable(file_path):
    '''

    :param file_path: requested client file
    :return: if user has access return True else False
    '''
    st = os.stat(file_path)
    return bool(st.st_mode & stat.S_IRGRP)


def download_files(request_file, path):
    '''
    Download files if not present at local directory
    :param request_file: requested client file
    :param path: root directory path
    :return: status code: if the file got downloaded sends 200 else 404
    '''
    url = "http://www.scu.edu/" + request_file
    img_data = requests.get(url)
    if img_data.status_code == 404:
        return img_data.status_code

    if not Path(path).is_dir():
        print("Inside path", path, request_file)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError:
            print("Creation of directory %s failed " % path)
        else:
            print("Directory %s created" % path)

    with open(path, 'wb') as handler:
        handler.write(img_data.content)
    return img_data.status_code


def get_content_type(file_name):
    '''

    :param file_name: requested client file
    :return: mime_type necessary for Content-type header
    '''
    if file_name.endswith(".jpg") or file_name.endswith(".jpeg"):
        mime_type = 'image/jpg'
    elif file_name.endswith(".png"):
        mime_type = 'image/png'
    elif file_name.endswith(".css"):
        mime_type = 'text/css'
    elif file_name.endswith(".gif"):
        mime_type = 'text/gif'
    elif file_name.endswith(".class"):
        mime_type = 'application/octet-stream'
    elif file_name.endswith(".htm") or file_name.endswith(".html"):
        mime_type = 'text/html'
    else:
        mime_type = 'text/plain'
    return mime_type


def parse_arguments():
    '''
    Parse document root and port value from commandline
    :return: arguments parsed from the commandline
    '''
    parser = argparse.ArgumentParser(description='Start a web server on port 8085')
    parser.add_argument('-document_root', dest='DOCUMENT_ROOT', action='store', help='Root location',
                        default='/Users/minalshettigar/Projects/')
    parser.add_argument('-PORT', dest='PORT', type=int, default='8085')
    result = parser.parse_args()
    return result



args = parse_arguments()
DOCUMENT_ROOT = args.DOCUMENT_ROOT
PORT = args.PORT
HOST = '127.0.0.1'

'''
Setup a socket connection with client, bind it to the port and host
'''
my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
my_socket.bind((HOST, PORT))
my_socket.listen(1)
threads = []
header = ''

print('Serving on port ', PORT)

'''
Initiate forever loop to accept client requests
'''
while True:
    connection, address = my_socket.accept()
    request = connection.recv(1024).decode('utf-8')
    string_list = request.split(' ')  # Split request from spaces
    method = string_list[0]
    if request != '':
        requesting_file = string_list[1]
        requesting_file = requesting_file.split('?')[0]  # After the "?" symbol not relevent here
    else:
        requesting_file = '/'
    print('Client request ', method, requesting_file)

    if method == 'GET' or method == 'HEAD':
        newClientThread = ClientRequestThread(PORT, HOST, requesting_file, DOCUMENT_ROOT)
        newClientThread.start()
        threads.append(newClientThread)
    else:
        ''' If method type is anythong other than get or head throw 500 error'''
        print("Status : 500 - Not Implemented %s method." % method)
        header = "HTTP/1.0 501 Not Implemented"
        header += 'Content-Type: ' + str(get_content_type(requesting_file)) + '\n\n'
        header += 'Content-Length: ' + str(0) + '\n\n'
        header += 'Date: ' + str(datetime.datetime.now()) + '\n\n'
        print("HEADERS: ", header)
        header = header.encode('utf-8')
        connection.send(header)
        connection.close()

    for t in threads:
        t.join()
