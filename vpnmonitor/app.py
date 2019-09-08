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

oifs:list = []
default_routes: list = []

print('Verificando intefaces de rede')


def store_default_routes(ipdb: object):
    global oifs, default_routes
    oifs = []
    default_routes = []
    interfaces: list = [x for x in getnic.interfaces() if (x != 'lo')]
    for interface in interfaces:
        try:
            index: int = ipdb.interfaces[interface].get('index')
            oifs.append(index)
            default_routes.append(ipdb.routes[{'dst': 'default', 'family': AF_INET, 'oif': index}])
        except KeyError:
            pass


print('Verificando rotas de rede')
ipdb: IPDB = IPDB()
store_default_routes(ipdb)


def delete_route(ipdb: object, route: object):
    for default_route in default_routes:
        if route.get_attr('RTA_OIF') == default_route.get('oif'):
            print('[watchdog]', 'Apagando a rota', route)
            ipdb.routes.remove({'dst': 'default',
                                'family': AF_INET,
                                'oif': route.get_attr('RTA_OIF'),
                                'gateway': route.get_attr('RTA_GATEWAY'),
                                'priority': route.get_attr('RTA_PRIORITY')})
            ipdb.commit()
            try:
                ipdb.routes[{'dst': 'default', 'family': AF_INET, 'oif': route.get_attr('RTA_OIF')}]
            except KeyError:
                ipdb.routes.add({'dst': 'default',
                                 'family': AF_INET,
                                 'oif': route.get_attr('RTA_OIF'),
                                 'gateway': route.get_attr('RTA_GATEWAY'),
                                 'priority': default_route.get('priority') or DEFAULT_PRIORITY,
                                 'scope': route.get('scope'),
                                 'dst_len': route.get('dst_len'),
                                 'src_len': route.get('src_len'),
                                 'tos': route.get('tos'),
                                 'flags': route.get('flags'),
                                 'type': route.get('type'),
                                 'proto': route.get('proto')})
                ipdb.commit()


def watchdog_callback(ipdb: object, message: object, action: object):
    global oifs, default_routes
    if action in ('RTM_NEWADDR', 'RTM_NEWLINK'):
        store_default_routes(ipdb)
        print('[watchdog]', action, 'Rotas default:', default_routes)
    if action == 'RTM_NEWROUTE':
        if message.get('family') == AF_INET \
                and message.get_attr('RTA_OIF') in oifs \
                and 20000 < message.get_attr('RTA_PRIORITY') < 21000:
            print('[watchdog]', action, 'Nova rota: ', message)
            delete_route(ipdb, message)


print('Inicializando watchdog')
watchdog: Watchdog = ipdb.watchdog()
watchdog.wait()

print('Registrando callback')
callback: int = ipdb.register_callback(watchdog_callback)

print('Monitorando rotas de rede... <[CTRL] + C> para encerrar!')
while keep_running:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

print('Des-registrando callback')
ipdb.unregister_callback(callback)
print('Finalizando watchdog')
ipdb.release()
print('Terminando... Laterz!')
