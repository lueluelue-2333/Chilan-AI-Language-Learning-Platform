import dashscope

# 替换成你的阿里 Key
dashscope.api_key = "sk-4b9d3525b789440e8a57e92bb05eb576"

def test_ali():
    resp = dashscope.TextEmbedding.call(
        model="text-embedding-v3",
        input="测试一下"
    )
    if resp.status_code == 200:
        print("✅ 阿里模型连接成功！")
        print(f"向量长度: {len(resp.output['embeddings'][0]['embedding'])}")
    else:
        print(f"❌ 错误代码: {resp.code}")
        print(f"❌ 错误信息: {resp.message}")

if __name__ == "__main__":
    test_ali()