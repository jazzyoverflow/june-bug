import requests
import logging
import base64
import time
import preprocessor
import classifier
import data_collector

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Server(object):
    url = 'https://mlb.praetorian.com'
    log = logging.getLogger(__name__)

    def __init__(self):
        self.session = requests.session()
        self.binary  = None
        self.hash    = None
        self.wins    = 0
        self.targets = []

    def _request(self, route, method='get', data=None):
        while True:
            try:
                if method == 'get':
                    r = self.session.get(self.url + route)
                else:
                    r = self.session.post(self.url + route, data=data)
                if r.status_code == 429:
                    raise Exception('Rate Limit Exception')
                if r.status_code == 500:
                    raise Exception('Unknown Server Exception')

                return r.json()
            except Exception as e:
                self.log.error(e)
                self.log.info('Waiting 60 seconds before next request')
                time.sleep(60)

    def get(self):
        r = self._request("/challenge")
        self.targets = r.get('target', [])
        self.binary  = base64.b64decode(r.get('binary', ''))
        return r

    def post(self, target):
        r = self._request("/solve", method="post", data={"target": target})
        self.wins = r.get('correct', 0)
        self.hash = r.get('hash', self.hash)
        self.ans  = r.get('target', 'unknown')
        return r

    def save_test_data(self, training_data, data_file_path, binary, possible_labels, answer):
        """
        optional functionality that allows the user to save test data 
        allowing for less data waste than just disposing of observations
        after attempting to predict
        """
        print(type(training_data))
        new_obs = {"blob": binary, "possible_ISAs": possible_labels, "label": answer}
        training_data.append(new_obs)
        with open(data_file_path, 'w') as file:
            json.dump(training_data, file)

        return

if __name__ == "__main__":

    # create the server object
    s = Server()

    # create the preprocessor object
    preprocessor = preprocessor.Preprocessor()

    # collect 300,000 observations
    # uncomment below if data is needed
    #data_collector.collect(s, 300000, preprocessor.raw_data_file)

    # extract TF-IDF vector and populate feature matrix and label vector
    feature_matrix = preprocessor.preprocess()
    print('gpt here')
    # create the classifier object
    classifier = classifier.Classifier(feature_matrix, preprocessor.labels, preprocessor.token_vec)
    
    # train the model given the collected observations and labels
    classifier.train()


     
    for _ in range(1000):
        # query the /challenge endpoint
        s.get()

        # preprocess using the blob and possible ISAs
        observation = preprocessor.prediction_preprocess(s.binary, s.targets) 

        # make prediction!
        target = classifier.predict(observation)
        s.post(target)
        
        s.save_test_data(preprocessor.raw_data, preprocessor.raw_data_file, s.binary, s.targets, s.ans)
        s.log.info("Guess:[{: >9}]   Answer:[{: >9}]   Wins:[{: >3}]".format(target, s.ans, s.wins))
        

        # 500 consecutive correct answers are required to win
        # very very unlikely with current code
        if s.hash:
            s.log.info("You win! {}".format(s.hash))

    
