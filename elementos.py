class Proyect:
    def __init__(self , name):
        self.name = name
        try:
            self.validate_proyect()
        except:
            pass

    def validate_proyect(self):
        pass

    def extract_clusters(self , proyect_name:str) -> list:
        pass

class Cluster:
    def __init__(self , name):
        pass

    def extract_namespaces(proyect_name:str) -> list:
        pass

class Namespace:
    def extract_deployments(proyect_name:str) -> list:
        pass

class Deployment:
    def extract_pipeline(self):
        pass

    def extract_pods(proyect_name:str) -> list:
        pass

    def set_config(self, config):
        pass

class Pod:
    def __init__(self):
        pass
