require('./mod')
require('./challenge_payload_bootstrap')
require('./challenge_payload_runner')

function get_cookie() {
    return document.cookie;
}

console.log(get_cookie());
