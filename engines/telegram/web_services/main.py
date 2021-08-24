import sys

sys.path.append("../../..")

import requests
from flask import Flask, request, render_template, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import Services
from sql import Sql

app = Flask(__name__)
auth = HTTPBasicAuth()
sql = Sql('../NanoBomber.db')

users = {
    "nanobomb": generate_password_hash("EdMaN1337")
}


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username


@app.route('/')
@auth.login_required
def index():
    return redirect('/services')


@app.route('/services', methods=['get'])
@auth.login_required
def services():
    if request.method.lower() == 'get':
        action = request.args.get('action')
        serv_id = request.args.get('id')
        if action == 'delete':
            sql.query("DELETE FROM services WHERE id = ?", [serv_id])
        elif action == 'test':
            return redirect(f'/test_service?id={serv_id}')
        return render_template('services_list.html', services=sql.query("SELECT * FROM services"))


@app.route('/test_service', methods=['get'])
def test_service():
    service_id = request.args.get('id')
    phone = request.args.get('phone')
    if service_id and phone:
        service = sql.query("SELECT * FROM services WHERE id = ?", [service_id])
        if not service:
            return redirect('/services')
        else:
            service = service[0]
        phone = Services.Phone(phone)
        if not phone.valid:
            return render_template("get_phone.html", service_id=service_id)
        if service.region:
            if phone.region not in service.region:
                return render_template("get_phone.html", service_id=service_id)
        try:
            service = Services.Services(phone).prepare_service(
                Services.Service(
                    service.method,
                    service.url,
                    service.params,
                    service.headers,
                    service.data,
                    service.json
                )
            )
            req = requests.request(**service.__dict__, verify=False)
            try:
                response_data = req.json()
                data_type = "Json"
            except:
                response_data = req.text
                data_type = "Text"

            return render_template('http_answer2.html', service_id=service_id, req=req, response_data=response_data,
                                   data_type=data_type, phone=phone.number)

        except Exception as err:
            return str(err)

    elif service_id:
        return render_template("get_phone.html", service_id=service_id)
    else:
        return redirect('/services')


@app.route('/new_service', methods=['get', 'post'])
@auth.login_required
def new_service():
    if request.method.lower() == 'get':
        return render_template('new_service.html')
    else:
        if request.form.get('req_type') == 'Test':
            try:
                service = Services.Services(Services.Phone(request.form.get('phone'))).prepare_service(
                    Services.Service(
                        request.form.get('method'),
                        request.form.get('url'),
                        request.form.get('params'),
                        request.form.get('headers'),
                        request.form.get('data'),
                        request.form.get('json')
                    )
                )

                req = requests.request(**service.__dict__, verify=False)
                try:
                    response_data = req.json()
                    data_type = "Json"
                except:
                    response_data = req.text
                    data_type = "Text"

                return render_template(
                    "http_answer.html",
                    req=req, response_data=response_data, data_type=data_type, **request.form.to_dict()
                )
            except Exception as err:
                return str(err)
        elif request.form.get('req_type') == 'Edit':
            return render_template("staryj_service.html", **request.form.to_dict())
        elif request.form.get('req_type') == 'Add':
            sql.query(
                "INSERT INTO services(method, url, params, headers, data, json, region) VALUES(?, ?, ?, ?, ?, ?, ?)",
                [
                    request.form.get('method') if request.form.get('method') else None,
                    request.form.get('url') if request.form.get('url') else None,
                    request.form.get('params') if request.form.get('params') else None,
                    request.form.get('headers') if request.form.get('headers') else None,
                    request.form.get('data') if request.form.get('data') else None,
                    request.form.get('json') if request.form.get('json') else None,
                    request.form.get('region') if request.form.get('region') else None
                ]
            )
            return redirect('/services')
        return '2'


@app.route('/count_of_services', methods=['get'])
def serv_count():
    return str(sql.query("SELECT COUNT(url) FROM services")[0].COUNTurl)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
