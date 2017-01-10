package org.alfresco.devops;

import java.io.IOException;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Map;

import org.apache.commons.lang3.exception.ExceptionUtils;

import com.amazonaws.SdkClientException;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.ListVersionsRequest;
import com.amazonaws.services.s3.model.S3VersionSummary;
import com.amazonaws.services.s3.model.VersionListing;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

public class EmptyBucktetsLambdaFunctionHandler implements RequestHandler<Map<String,Object>, Object> {

	private static enum Status {
		SUCCESS, FAILED
	}

	@Override
	public Object handleRequest(Map<String,Object> input , Context context) {

		LambdaLogger logger = context.getLogger();

		String requestType = (String)input.get("RequestType");

		@SuppressWarnings("unchecked")
		Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
		String bucketName = (String) resourceProps.get("BucketName");

		AmazonS3 s3 = new AmazonS3Client();

		if(!requestType.equalsIgnoreCase("Delete")){
			logger.log("[INFO] RequestType "+ requestType +" -> exit");
			sendMessage(input, Status.SUCCESS,context);
			return null;
		}

		try{
			if(!s3.doesBucketExist(bucketName)){
				logger.log("[WARN] Bucket "+ bucketName +" does not exist -> exit");
				sendMessage(input, Status.SUCCESS,context);
				return null;
			}
			logger.log("[INFO] bucket "+bucketName+" deleting content");
			deleteAllVersions(bucketName, s3);
			logger.log("[INFO] bucket "+bucketName+" content deleted!");
			logger.log("[INFO] deleting bucket "+bucketName);
			s3.deleteBucket(bucketName);
			logger.log("[INFO] bucket "+ bucketName +" deleted!");
			sendMessage(input, Status.SUCCESS,context);
			return null;
		}
		catch (SdkClientException  sce) {
			String st = ExceptionUtils.getStackTrace(sce);
			logger.log("[ERROR] Not possible to delete "+ bucketName + "\nStackTrace "+st);
			sendMessage(input, Status.FAILED,context);
			return null;
		}

	}

	private void sendMessage(Map<String, Object> input, Status status, Context context) {

		LambdaLogger logger = context.getLogger();
		String responseURL = (String)input.get("ResponseURL");
		try {
			URL url = new URL(responseURL);
			HttpURLConnection connection=(HttpURLConnection)url.openConnection();
			connection.setDoOutput(true);
			connection.setRequestMethod("PUT");

			@SuppressWarnings("unchecked")
			Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
			String bucketName = (String) resourceProps.get("BucketName");

			OutputStreamWriter out = new OutputStreamWriter(connection.getOutputStream());
			ObjectMapper mapper = new ObjectMapper();
			
			ObjectNode cloudFormationJsonResponse = mapper.createObjectNode();
			cloudFormationJsonResponse.put("Status", status.toString());
			cloudFormationJsonResponse.put("PhysicalResourceId", bucketName +(String)input.get("LogicalResourceId"));
			cloudFormationJsonResponse.put("StackId", (String)input.get("StackId"));
			cloudFormationJsonResponse.put("RequestId", (String)input.get("RequestId"));
			cloudFormationJsonResponse.put("LogicalResourceId", (String)input.get("LogicalResourceId"));
			cloudFormationJsonResponse.put("Reason", "See details in CloudWatch Log StreamName " + context.getLogStreamName() +" ** GroupName: "+context.getLogGroupName());
			String cfnResp = cloudFormationJsonResponse.toString();
			logger.log("[DEBUG] CF Json repsonse "+cfnResp);
			out.write(cfnResp);
			out.close();
			int responseCode = connection.getResponseCode();
			logger.log("[INFO] Response Code "+responseCode);
		} catch (IOException e) {
			String st = ExceptionUtils.getStackTrace(e);
			logger.log("[ERROR] Not able to send message to CF Template \nStackTrace "+st);
		}
	}

	private void deleteAllVersions(String bucketName, AmazonS3 s3){
		VersionListing version_listing = s3.listVersions(new ListVersionsRequest().withBucketName(bucketName));
		while (true) {
			for (S3VersionSummary vs : version_listing.getVersionSummaries()) {
				s3.deleteVersion(bucketName, vs.getKey(), vs.getVersionId());
			}
			if (version_listing.isTruncated()) {
				version_listing = s3.listNextBatchOfVersions(version_listing);
			} else {
				break;
			}
		}
	}
}

