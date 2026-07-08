from locust import HttpUser, task, between


class SockShopUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def browse_homepage(self):
        self.client.get("/")

    @task(2)
    def browse_catalogue(self):
        self.client.get("/catalogue")

    @task(1)
    def view_items(self):
        self.client.get("/catalogue?size=3")