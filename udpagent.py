import logging
import logging.handlers
import logging.config
import ConfigParser
import socket
import msgpack
from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
import six
import uuid
import datetime
from oslo_utils import netutils
from oslo_utils import timeutils
from oslo_utils import units



#logging.config.fileConfig('udpagent.conf', disable_existing_loggers=False)
class UdpService():
    def __init__(self):
        config = ConfigParser.ConfigParser()
        config.read('udpagent.conf')
        self.udp_address      =  config.get('udpservice','udp_address')
        self.udp_port         =  int(config.get('udpservice','udp_port')) 
        self.rabbit_user      =  config.get('udpservice','rabbit_userid')
        self.rabbit_password  =  config.get('udpservice','rabbit_password') 
        self.rabbit_host      =  config.get('udpservice','rabbit_hosts')
        self.acord_control_exchange = config.get('udpservice','acord_control_exchange') 
        logging.config.fileConfig('udpagent.conf', disable_existing_loggers=False)
    def printconfig(self):
        logging.debug("udp_address:%s",self.udp_address) 
        logging.debug("udp_port:%s",self.udp_port)  
        logging.debug("rabbit_user:%s",self.rabbit_user)  
        logging.debug("rabbit_password:%s",self.rabbit_password)  
        logging.debug("rabbit_hosts:%s",self.rabbit_host)  
        logging.debug("cord_control_exchange:%s",self.acord_control_exchange)
   
    def convert_sample_to_event_data(self,msg):
        event_data = {'event_type': 'infra','message_id':six.text_type(uuid.uuid4()),'publisher_id': 'cpe_publisher_id','timestamp':datetime.datetime.now().isoformat(),'priority':'INFO','payload':msg}
        return event_data
   
    def setup_rabbit_mq_channel(self):
        service_exchange = Exchange(self.acord_control_exchange, "topic", durable=False)
        # connections/channels
        connection = BrokerConnection(self.rabbit_host, self.rabbit_user, self.rabbit_password)
        logging.info("Connection to RabbitMQ server successful")
        channel = connection.channel()
        # produce
        self.producer = Producer(channel, exchange=service_exchange, routing_key='notifications.info')

    def start_udp(self):
        address_family = socket.AF_INET
        if netutils.is_valid_ipv6(self.udp_address):
            address_family = socket.AF_INET6
        udp = socket.socket(address_family, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind((self.udp_address,
                  self.udp_port))

        self.setup_rabbit_mq_channel()
        self.udp_run = True
        while self.udp_run:
            # NOTE(jd) Arbitrary limit of 64K because that ought to be
            # enough for anybody.
            data, source = udp.recvfrom(64 * units.Ki)
            try:
                sample = msgpack.loads(data, encoding='utf-8')
            except Exception:
                logging.warning("UDP: Cannot decode data sent by %s", source)
            else:
                try:
                    if sample.has_key("event_type"):
                         logging.debug("recevied event  :%s",sample)
                         self.producer.publish(sample)
                    else:
                         logging.debug("recevied Sample  :%s",sample)
                         msg = self.convert_sample_to_event_data(sample)
                         self.producer.publish(msg)
                except Exception:
                    logging.exception("UDP: Unable to publish msg")
       

def main():
    try:
        udpservice=UdpService()
        udpservice.printconfig()
        udpservice.start_udp()  

    except Exception as e:
        logging.exception("* Error in starting udpagent:%s",e.__str__())
    


if __name__ == "__main__":
    main() 
