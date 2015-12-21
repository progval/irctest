"""
Handles ambiguities of RFCs.
"""

def normalize_namreply_params(params):
    # So… RFC 2812 says:
    #       "( "=" / "*" / "@" ) <channel>
    #       :[ "@" / "+" ] <nick> *( " " [ "@" / "+" ] <nick> )
    # but spaces seem to be missing (eg. before the colon), so we
    # don't know if there should be one before the <channel> and its
    # prefix.
    # So let's normalize this to “with space”, and strip spaces at the
    # end of the nick list.
    if len(params) == 3:
        assert params[1][0] in '=*@', params
        params.insert(1), params[1][0]
        params[2] = params[2][1:]
    params[3] = params[3].rstrip()
    return params
