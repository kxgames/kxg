import network

class Broker:

    def publish(self, message):
        pass

    def subscribe(self, flavor, callback):
        pass

    def unsubscribe(self, flavor, callback):
        pass

class SandboxBroker(Broker):
    pass

class ClientBroker(Broker):

    def __init__(self, client):
        self.client = client

class ServerBroker(Broker):

    def __init__(self, clients):
        self.clients = clients

class Conversation:
    pass

class ClientConversation(Conversation):
    pass

class ServerConversation(Conversation):
    pass


