import os
import signal
import time
from _socket import AF_INET

from get_nic import getnic
from pyroute2 import IPDB
from pyroute2.ipdb.main import Watchdog

DEFAULT_PRIORITY: int = 256

print('Verificando permissoes de root')
if os.geteuid() != 0:
    print('Saindo! Necessario permissoes de root')
    exit()

keep_running: bool = True


def exit_gracefully(signum: object, frame: object):
    global keep_running
    keep_running = False


print('Inicializando...')
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

oifs: list = []


def store_interfaces_oifs(ipdb: object):
    try:
        global oifs
        oifs = []
        interfaces: list = [x for x in getnic.interfaces() if (x != 'lo')]
        for interface in interfaces:
            index: int = ipdb.interfaces[interface].get('index')
        oifs.append(index)
    finally:
        print('Monitorando intefaces de rede: ', oifs)


def get_default_routes(ipdb: object):
    try:
        global oifs
        default_routes = ipdb.routes.filter('default')
        routes = [x.get('route') for x in default_routes]
        return [x for x in routes if x.get('family') == AF_INET and x.get('oif') in oifs]
    except KeyError:
        return []


def verify_valid_route(ipdb: object, oif: int, gateway: str):
    try:
        routes = get_default_routes(ipdb)
        if len([x for x in routes if x.get('oif') == oif
                                     and x.get('gateway') == gateway
                                     and 0 < x.get('priority') < 2000]) != 0:
            return True
        return False
    except:
        return False


def delete_invalid_route(ipdb: object, oif: int, gateway: str):
    try:
        routes = get_default_routes(ipdb)
        invalid_routes = [x for x in routes if x.get('oif') == oif
                          and x.get('gateway') == gateway
                          and 20000 < x.get('priority') < 21000]
        for invalid_route in invalid_routes:
            print('[watchdog]', 'Apagando rota invalida', invalid_route)
            ipdb.routes.remove({'dst': 'default',
                                'family': AF_INET,
                                'oif': invalid_route.get('oif'),
                                'gateway': invalid_route.get('gateway'),
                                'priority': invalid_route.get('priority')})
            ipdb.commit()
    except:
        pass


def watchdog_callback(ipdb: object, message: object, action: object):
    global oifs
    if action in ('RTM_NEWADDR', 'RTM_NEWLINK') \
            and ipdb.interfaces[message.get_attr('RTA_OIF')].get('operstate') == 'UP':
        store_interfaces_oifs(ipdb)
    if action == 'RTM_NEWROUTE':
        if message.get('family') == AF_INET \
                and message.get_attr('RTA_OIF') in oifs \
                and 20000 < message.get_attr('RTA_PRIORITY') < 21000:
            if verify_valid_route(ipdb, message.get_attr('RTA_OIF'), message.get_attr('RTA_GATEWAY')):
                print('[watchdog]', action, 'Encontrado rota invalida: ', message)
                delete_invalid_route(ipdb, message.get_attr('RTA_OIF'), message.get_attr('RTA_GATEWAY'))


print('Verificando rotas de rede')
main_ipdb: IPDB = IPDB()
store_interfaces_oifs(main_ipdb)

print('Inicializando watchdog')
watchdog: Watchdog = main_ipdb.watchdog()
watchdog.wait()

print('Registrando callback')
callback: int = main_ipdb.register_callback(watchdog_callback)

print('Validando rotas atuais')
try:
    routes = get_default_routes(main_ipdb)
    routes = [x for x in routes if 20000 < x.get('priority') < 21000]
    if len(routes) != 0:
        for route in routes:
            if verify_valid_route(main_ipdb, route.get('oif'), route.get('gateway')):
                print('[watchdog]', 'Encontrado rota invalida: ', route)
                delete_invalid_route(main_ipdb, route.get('oif'), route.get('gateway'))
except:
    pass

print('Monitorando rotas de rede... <[CTRL] + C> para encerrar!')
while keep_running:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

print('Des-registrando callback')
main_ipdb.unregister_callback(callback)
print('Finalizando watchdog')
main_ipdb.release()
print('Terminando... Laterz!')
