import sys
sys.path.insert(0, '..')

import asyncio
from astrnet.schema import app, schema

async def test():
    # 启动broker
    await app.broker.startup()
    
    query = '{ echo(message: "hello") }'
    result = await schema.execute(query)
    print('Result:', result)
    print('Data:', result.data)
    if result.errors:
        print('Errors:', result.errors)
    
    # 关闭broker
    await app.broker.shutdown()

if __name__ == "__main__":
    asyncio.run(test())