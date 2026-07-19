import json


class JsonUtils:

    @staticmethod
    def loads(text: str):

        return json.loads(text)

    @staticmethod
    def dumps(data):

        return json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )