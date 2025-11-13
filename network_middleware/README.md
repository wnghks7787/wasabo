직접적으로 건들 만한 부분은 main.py이다.    
```cms_crawler``` 에서 필요한 코드들을 import 하여 사용한다.    
원하는 미들웨어를 ```MIDDLEWARE```에 맞춰주고, ```MAX_WORKER```를 조정해준 다음 실행시키면 알아서 작동한다. 
작동을 시작하면 ```cms_crawler```에서 만들었던 compose files를 기준으로 모든 도커 이미지를 compose-up을 하고, 초기 설정 페이지를 지나게 한 뒤, wasabo의 testbed 안으로 넣어주게 된다.   
wasabo에서 사용할 도구를 변경하기 위해서는 ```testbeds/fingerprint/testbed.py```에서 코드를 수정해야 한다.  
주석처리 되어있는 Whatweb, Wappalyzer 등의 주석을 해제하면 해당 부분이 results 파일에 생성된다. 

만약 fingperprinting tools가 없다면 WASABO의 dockerfile을 통해 다운로드 받으면 된다.