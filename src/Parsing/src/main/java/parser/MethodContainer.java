package parser;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class MethodContainer {
    private List<String> nameTokens = new ArrayList<>();
    private List<String> bodyTokens = new ArrayList<>();
    private List<String> apiCalls = new ArrayList<>();

    public void addNameToken(String token) {
        nameTokens.add(token);
    }

    public void addBodyToken(String token) {
        bodyTokens.add(token);
    }

    public void addApiCall(String call) {
        apiCalls.add(call);
    }

    public void addAllNameToken(Collection<String> tokens) {
        nameTokens.addAll(tokens);
    }

    public void addAllBodyToken(Collection<String> tokens) {
        bodyTokens.addAll(tokens);
    }

    public void addAllApiCall(Collection<String> calls) {
        apiCalls.addAll(calls);
    }

    public List<String> getNameTokens() {
        return nameTokens;
    }

    public List<String> getBodyTokens() {
        return bodyTokens;
    }

    public List<String> getApiCalls() {
        return apiCalls;
    }

    @Override
    public String toString() {
        return "MethodContainer{" +
                "nameTokens=" + nameTokens +
                ", bodyTokens=" + bodyTokens +
                ", apiCalls=" + apiCalls +
                '}';
    }
}
