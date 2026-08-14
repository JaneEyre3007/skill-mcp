require('./mod')

// 源码区域
'challenge_payload_bootstrap';
'challenge_payload_runner';

function get_cookie() {
    return document.cookie;
}

console.log(get_cookie());
