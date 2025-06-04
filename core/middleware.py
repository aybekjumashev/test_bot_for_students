import asyncio
from asgiref.sync import sync_to_async, AsyncToSync

class AsyncMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.sync_get_response = sync_to_async(get_response)

    def __call__(self, request):
        if asyncio.iscoroutinefunction(self.get_response):
            return self.async_call(request)
        return AsyncToSync(self.async_call)(request)

    async def async_call(self, request):
        if response := await self.process_request(request):
            return response
        response = await self.sync_get_response(request)
        return await self.process_response(request, response)

    async def process_request(self, request):
        return None

    async def process_response(self, request, response):
        return response
