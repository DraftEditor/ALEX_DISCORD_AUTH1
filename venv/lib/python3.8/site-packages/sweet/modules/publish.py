import time

keywords = {                            # 定义关键字
    '诗歌': 'POETRY',                   # key 为关键字，英文须大写，value 是对应的函数名  
    'POETRY': 'POETRY'                  # 关键字建议中、英文各定义一份
}


class App:                              # 约定 

    keywords = keywords                 # 约定

    def __init__(self, setting):        # 约定，setting 是 element 中定义的字典

        self.header = setting['header'] # 示例，根据需要提取 setting 参数
        self.footer = setting['footer']

    def _close(self):                   # 约定，自动化退出时，执行的清理函数

        pass                            # 根据需要编写，请参考 web 实现

    def _call(self, step):              # 约定，step 为用例步骤

        # 根据关键字调用关键字实现
        getattr(self, step['keyword'].lower())(step)  # 约定，调用关键字函数

    def poetry(self, step):             # 需自己实现的关键字函数
        title = step['element']
        data = step['data']
        text = data['text']
        time.sleep(0.2)
        print(f'{self.header*22}\n')
        print(f'{" "*8}{title}\n')
        print(f'{text}\n')
        print(f'{self.footer*22}')
