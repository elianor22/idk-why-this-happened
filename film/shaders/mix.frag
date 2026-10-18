#version 430
uniform sampler2D uA;
uniform sampler2D uB;
uniform sampler2D uTxtMain;
uniform sampler2D uTxtHud;
uniform float uGainMain;
uniform float uGainHud;
uniform int uMode;
uniform float uM;       // 0..1 transition progress
uniform vec2 uRes;
uniform vec2 uIrisC;
out vec4 o;
void main(){
    vec2 uv = gl_FragCoord.xy / uRes;
    vec3 a = texture(uA, uv).rgb;
    vec3 b = texture(uB, uv).rgb;
    vec3 c;
    if (uMode == 0){ c = a; }
    else if (uMode == 1){            // soft crossfade
        float m = smoothstep(0.0, 1.0, uM); c = mix(a, b, m);
    } else if (uMode == 2){          // hard cut with light spike
        c = (uM < 0.5) ? a : b;
        float sp = exp(-abs(uM - 0.5) * 22.0);
        c += vec3(0.8, 0.9, 1.0) * sp * 1.2;
    } else if (uMode == 3){          // iris from point, glowing edge
        vec2 p = (gl_FragCoord.xy - uIrisC * uRes) / uRes.y;
        float far = length(max(abs(uIrisC - 0.5) , vec2(0.0)) * 0.0) + 1.6;
        float r = uM * uM * (3.0 - 2.0 * uM) * far;
        float d = length(p);
        float edge = smoothstep(r + 0.004, r - 0.004, d);
        c = mix(a, b, edge);
        float ring = exp(-abs(d - r) * 90.0) * smoothstep(0.0, 0.08, uM) * (1.0 - smoothstep(0.85, 1.0, uM));
        c += vec3(1.0, 0.85, 0.6) * ring * 1.4;
    }
    vec4 t1 = texture(uTxtMain, vec2(uv.x, 1.0 - uv.y));
    vec4 t2 = texture(uTxtHud, vec2(uv.x, 1.0 - uv.y));
    c = c * (1.0 - t1.a) + t1.rgb * uGainMain;
    c = c * (1.0 - t2.a) + t2.rgb * uGainHud;
    o = vec4(c, 1.0);
}
