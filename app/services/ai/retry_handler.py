"""
AI Retry Handler.
"""

import time



class RetryHandler:

    def __init__(
        self,
        retries: int = 3,
        delay: float = 2,
    ):

        self.retries = retries
        self.delay = delay



    def execute(
        self,
        func,
        *args,
        **kwargs,
    ):


        last_exception = None


        for attempt in range(
            self.retries
        ):

            try:

                return func(
                    *args,
                    **kwargs
                )


            except Exception as exc:

                last_exception = exc


                if attempt < self.retries - 1:

                    time.sleep(
                        self.delay
                    )


        raise last_exception